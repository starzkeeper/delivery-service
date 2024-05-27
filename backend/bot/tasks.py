import asyncio
import threading

from handlers.delivery_handlers import (
    delivery_cancelled_by_consumer_notification,
    delivery_taking_late_notification,
    delivery_time_out_notification,
    send_delivery_info_msg,
)
from logging_.logger import logger
from services.delivery_service import DeliveryCancellationService, DeliveryService
from services.metrics_service import AvgCourierSpeedProvider
from services.notification_service import NotificationService
from telegram import Update
from telegram.ext import CallbackContext
from utils import DistanceCalculator


async def distribute_deliveries_periodic_task(context: CallbackContext):
    service = DeliveryService()
    deliveries_ = await service.start_delivering()
    logger.warning('Starting deliveries')

    if deliveries_ is not None:
        async for delivery in deliveries_:
            logger.info(f'Got delivery {delivery} for delivering')
            if delivery['success']:
                await send_delivery_info_msg(
                    context,
                    chat_id=delivery['courier'].id,
                    delivery=delivery['delivery'],
                )
            else:
                logger.warning('No free couriers!')
    else:
        logger.warning('Distribution does not started because of not free couriers!')


async def check_cancelled_deliveries_periodic_task(context: CallbackContext):
    service = DeliveryCancellationService()
    couriers_to_notify = service.check_cancelled_deliveries()
    if couriers_to_notify:
        async for courier in couriers_to_notify:
            await delivery_cancelled_by_consumer_notification(context, courier)


async def delivery_notification_periodic_task(context: CallbackContext):
    service = NotificationService()
    to_notify_deliveries, time_out_deliveries = await service.distribute_notifications()
    for delivery in to_notify_deliveries:
        await delivery_taking_late_notification(context, delivery)
    for delivery in time_out_deliveries:
        await delivery_time_out_notification(context, delivery)


async def job_check_deliveries(update: Update, context: CallbackContext):
    job_queue = context.job_queue
    job_queue.run_repeating(distribute_deliveries_periodic_task, interval=5, first=0)


async def job_check_cancelled_deliveries(update: Update, context: CallbackContext):
    job_queue = context.job_queue
    job_queue.run_repeating(
        check_cancelled_deliveries_periodic_task, interval=5, first=0
    )


async def job_notify_courier(update: Update, context: CallbackContext):
    job_queue = context.job_queue
    job_queue.run_repeating(delivery_notification_periodic_task, interval=10, first=0)


async def collect_speed_metrics(update):
    metrics_collector = AvgCourierSpeedProvider()
    speed = await metrics_collector.get_avg_couriers_speed()
    logger.warning('CALCULATED AVG COURIERS SPEED: {}'.format(speed))
    if speed:
        DistanceCalculator.avg_courier_speed = speed


async def job_get_avg_couriers_speed(update: Update, context: CallbackContext):
    job_queue = context.job_queue
    # TODO: CHANGE INTERVAL FOR ABOUT 360 SECS!
    job_queue.run_repeating(collect_speed_metrics, interval=20, first=0)


async def run_jobs(update: Update, context: CallbackContext):
    jobs = (job_get_avg_couriers_speed,
            job_notify_courier,
            job_check_deliveries,
            job_check_cancelled_deliveries,)

    def between_callback(func, *args):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(func(*args))
        loop.close()

    for job in jobs:
        thread = threading.Thread(target=between_callback, args=(job, update, context,))
        thread.start()
