import logging

from delivery.models import Delivery
from django.core.serializers import serialize


class DeliveryAdapter:

    @staticmethod
    def update_delivery_in_db_from_telegrma(delivery_dict: dict) -> Delivery:
        try:
            cour_id = delivery_dict.pop('courier')
            delivery_dict['courier_id'] = cour_id
            d = Delivery.objects.filter(id=delivery_dict['id']).first()
            if d:
                for key, value in delivery_dict.items():
                    setattr(d, key, value)
                logging.info('(SUCCESS) Updated delivery in database!')
                d.save()
            return d
        except Exception as e:
            logging.error(f'Could not update delivery in db coz of {e}', exc_info=True)

    @staticmethod
    def serialize_delivery(delivery_orm: Delivery):
        serialized_delivery = serialize('json', [delivery_orm])
        return serialized_delivery
