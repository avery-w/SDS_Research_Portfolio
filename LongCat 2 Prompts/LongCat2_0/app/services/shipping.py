import requests
from flask import current_app


class ShippingService:
    SERVICE_MULTIPLIERS = {
        'ground': 1.0,
        '3day': 1.5,
        '2day': 2.0,
        'nextday': 3.0,
        'saver': 0.85
    }

    SERVICE_NAMES = {
        'ground': 'UPS Ground',
        '3day': 'UPS 3 Day Select',
        '2day': 'UPS 2nd Day Air',
        'nextday': 'UPS Next Day Air',
        'saver': 'UPS Saver'
    }

    SERVICE_DAYS = {
        'ground': '5-7 business days',
        '3day': '3 business days',
        '2day': '2 business days',
        'nextday': '1 business day',
        'saver': '4-6 business days'
    }

    def calculate_rate(self, weight=1.0, destination_zip='', destination_city='',
                       destination_state='', method='ground', length=12, width=9, height=6):
        if current_app.config.get('UPS_USE_MOCK', True):
            return self._mock_calculate_rate(
                weight, destination_zip, destination_city,
                destination_state, method, length, width, height
            )
        return self._ups_api_calculate_rate(
            weight, destination_zip, destination_city,
            destination_state, method, length, width, height
        )

    def _mock_calculate_rate(self, weight, destination_zip, destination_city,
                             destination_state, method, length, width, height):
        base_rate = current_app.config.get('SHIPPING_BASE_RATE', 5.99)
        per_item_rate = current_app.config.get('SHIPPING_PER_ITEM', 2.50)
        multiplier = self.SERVICE_MULTIPLIERS.get(method, 1.0)

        if weight <= 1:
            weight_charge = 0
        else:
            weight_charge = (weight - 1) * 1.50

        dimensional_weight = (length * width * height) / 139
        billable_weight = max(weight, dimensional_weight)

        distance_factor = 1.0
        if destination_zip:
            try:
                dest_prefix = int(destination_zip[:3])
                origin_zip = current_app.config['ORIGIN_ADDRESS']['zip']
                origin_prefix = int(origin_zip[:3])
                distance = abs(dest_prefix - origin_prefix)
                distance_factor = 1.0 + (distance * 0.002)
            except (ValueError, KeyError):
                pass

        rate = (base_rate + weight_charge) * multiplier * distance_factor
        rate = round(max(rate, 3.50), 2)

        return {
            'rate': rate,
            'method': method,
            'service_name': self.SERVICE_NAMES.get(method, 'UPS Ground'),
            'estimated_delivery': self.SERVICE_DAYS.get(method, '5-7 business days'),
            'weight': billable_weight,
            'origin': current_app.config.get('ORIGIN_ADDRESS', {}),
            'destination': {
                'zip': destination_zip,
                'city': destination_city,
                'state': destination_state
            }
        }

    def _ups_api_calculate_rate(self, weight, destination_zip, destination_city,
                                destination_state, method, length, width, height):
        api_key = current_app.config.get('UPS_API_KEY', '')
        api_url = current_app.config.get('UPS_API_URL', 'https://onlinetools.ups.com/api')

        if not api_key:
            return self._mock_calculate_rate(
                weight, destination_zip, destination_city,
                destination_state, method, length, width, height
            )

        service_codes = {
            'ground': '03',
            '3day': '12',
            '2day': '02',
            'nextday': '01',
            'saver': '13'
        }

        payload = {
            "RateRequest": {
                "Request": {
                    "TransactionReference": {"CustomerContext": "marketplace-rate-request"}
                },
                "Shipment": {
                    "Shipper": {
                        "Address": {
                            "AddressLine": [current_app.config['ORIGIN_ADDRESS']['street']],
                            "City": current_app.config['ORIGIN_ADDRESS']['city'],
                            "StateProvinceCode": current_app.config['ORIGIN_ADDRESS']['state'],
                            "PostalCode": current_app.config['ORIGIN_ADDRESS']['zip'],
                            "CountryCode": current_app.config['ORIGIN_ADDRESS']['country']
                        }
                    },
                    "ShipTo": {
                        "Address": {
                            "City": destination_city or '',
                            "StateProvinceCode": destination_state or '',
                            "PostalCode": destination_zip,
                            "CountryCode": "US"
                        }
                    },
                    "Package": {
                        "PackagingType": {"Code": "02"},
                        "PackageWeight": {
                            "UnitOfMeasurement": {"Code": "LBS"},
                            "Weight": str(weight)
                        },
                        "Dimensions": {
                            "UnitOfMeasurement": {"Code": "IN"},
                            "Length": str(length),
                            "Width": str(width),
                            "Height": str(height)
                        }
                    },
                    "Service": {"Code": service_codes.get(method, '03')}
                }
            }
        }

        try:
            response = requests.post(
                f"{api_url}/rating/v2403/Rate",
                json=payload,
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            rated_shipment = data['RateResponse']['RatedShipment']
            total_charges = rated_shipment['TotalCharges']

            return {
                'rate': float(total_charges['MonetaryValue']),
                'method': method,
                'service_name': self.SERVICE_NAMES.get(method, 'UPS Ground'),
                'estimated_delivery': rated_shipment.get(
                    'GuaranteedDelivery', {}
                ).get('BusinessDaysInTransit', '5-7 business days'),
                'weight': weight,
                'origin': current_app.config['ORIGIN_ADDRESS'],
                'destination': {
                    'zip': destination_zip,
                    'city': destination_city,
                    'state': destination_state
                }
            }
        except (requests.RequestException, KeyError, ValueError) as e:
            current_app.logger.error(f'UPS API error: {e}. Falling back to mock rates.')
            return self._mock_calculate_rate(
                weight, destination_zip, destination_city,
                destination_state, method, length, width, height
            )

    def get_available_methods(self):
        return [
            {'id': 'ground', 'name': 'UPS Ground', 'days': '5-7 business days'},
            {'id': '3day', 'name': 'UPS 3 Day Select', 'days': '3 business days'},
            {'id': '2day', 'name': 'UPS 2nd Day Air', 'days': '2 business days'},
            {'id': 'nextday', 'name': 'UPS Next Day Air', 'days': '1 business day'},
            {'id': 'saver', 'name': 'UPS Saver', 'days': '4-6 business days'}
        ]
