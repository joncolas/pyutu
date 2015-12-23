# Copyright (c) 2015 Brett Francis http://www.oort.org
#

import os, sys
import logging
import requests
import json
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache


__version__ = open(os.path.join(os.path.dirname(__file__), '_version')).read()


logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                    format="%(asctime)s: " + logging.BASIC_FORMAT,
                    datefmt="%Y-%m-%dT%H:%M:%S%z")
logger = logging.getLogger(__name__)

req = CacheControl(requests.Session(), cache=FileCache('pyutu.cache'))

regions = {
    'ap-northeast-1': "Asia Pacific (Tokyo)",
    'ap-southeast-1': "Asia Pacific (Singapore)",
    'ap-southeast-2': "Asia Pacific (Sydney)",
    'eu-central-1': "EU (Frankfurt)",
    'eu-west-1': "EU (Ireland)",
    'sa-east-1': "South America (Sao Paulo)",
    'us-east-1': "US East (N. Virginia)",
    'us-west-1': "US West (N. California)",
    'us-west-2': "US West (Oregon)"
}

svcs = {
    "ec2": {
        'offer_code': "AmazonEC2",
        'prod_families': {
            "Data Transfer": "fromLocation",
            "Compute Instance": "location",
            "IP Address": "location",
            "Dedicated Host": "location"
        }
    },
    "ses": {
        'offer_code': "AmazonSES",
        'prod_families': {
            "Data Transfer": "fromLocation",
            "Sending Email": "location"
        }
    },
    "ddb": {
        'offer_code': "AmazonDynamoDB",
        'prod_families': {
            "Data Transfer": "fromLocation",
            "Database Storage": "location",
            "Provisioned IOPS": "location"
        }
    },
    "s3": {
        'offer_code': "AmazonS3",
        'prod_families': {
            "Data Transfer": "fromLocation",
            "API Request": "location",
            "Storage": "location",
            "Fee": "location"
        }
    }
}
#     "glacier": "AmazonGlacier",
#     "cloudfront": "AmazonCloudFront",
#     "cf": "AmazonCloudFront",
#     "vpc": "AmazonVPC",
#     "kms": "awskms",
#     "rds": "AmazonRDS",
#     "route53": "AmazonRoute53",
#     "r53": "AmazonRoute53",
#     "redshift": "AmazonRedshift",
# }


class PricingContext(object):

    def __init__(self, region, service, root="https://pricing.us-east-1.amazonaws.com"):
        self.sku = None
        self.aws_root = root
        self.region = region
        self.aws_index = self.aws_root + "/offers/v1.0/aws/index.json"
        self.idx = req.get(self.aws_index).json()
        self.sku = None
        self.service = service
        self._terms = None
        self.attributes =

    @property
    def terms(self):
        if self._terms is None:
            self._terms = "OnDemand"
        return self._terms

    @terms.setter
    def terms(self, value):
        # maps any input value regardless of case to the AWS product term
        term_map = {'ondemand': "OnDemand", "reserved": "Reserved"}
        t = value.lower()
        self._terms = term_map[t]

    def add_attribute(self, values):
        if values is None:
            return

        if values is dict:


def set_debug():
    logger.setLevel(level=logging.DEBUG)


def check_service(svc):
    if svc not in svcs:
        raise ValueError('Invalid service: {0}'.format(svc))

    return True


def get_details(pc):
    logger.info("  Format Version: {0}".format(pc.idx['formatVersion']))
    logger.info("Publication Date: {0}".format(pc.idx['publicationDate']))
    olist = ''
    for i,o in enumerate(pc.idx['offers']):
        if i < len(pc.idx['offers']) - 1:
            olist += o + ", "
        else:
            olist += o

    logger.info("          Offers: {0}".format(olist))


def get_prices(pc):
    check_service(svc=pc.service)

    service_alias = svcs[pc.service]['offer_code']
    logger.info("Service Alias: {0}".format(service_alias))
    url = pc.aws_root + \
        pc.idx['offers'][service_alias]['currentVersionUrl']
    logger.info("          URL: {0}".format(url))
    logger.info("       Region: {0}".format(pc.region))
    logger.info("Product Terms: {0}".format(pc.terms))

    offer_file = req.get(url).json()

    logger.debug('Getting specific product SKU: {0}'.format(pc.sku))

    products = {}
    if pc.sku is None:
        for p in offer_file['products']:
            product = offer_file['products'][p]
            prod_fam = product['productFamily']
            if prod_fam in svcs[svc]['prod_families']:
                f2r = svcs[svc]['prod_families'][prod_fam]
                attr_val = product['attributes'][f2r]
                if attr_val == regions[pc.region]:
                    sku = product['sku']
                    logger.debug('Found product SKU: {0} in region: {1}'.format(
                        sku, pc.region
                    ))
                    match = _check_terms_attribs(pc, offer_file, product, sku)
                    logger.debug('Match is: {0}'.format(match))
                    if match:
                        products[sku] = match
    else:
        products[pc.sku] = {
            'offerCode': offer_file['offerCode'],
            'product': offer_file['products'][pc.sku],
            'term': offer_file['terms'][pc.terms][pc.sku]
        }

    logger.info("       Products:{0}".format(json.dumps(
        products, indent=2, sort_keys=True))
    )
    return products


def _check_terms_attribs(pc, offer_file, product, sku):
    logger.debug('Checking product terms: {0}'.format(pc.terms))
    try:
        terms = offer_file['terms'][pc.terms][sku]
        # checking attributes
        logger.debug('Checking product attributes: {0}'.format(
            pc.attributes
        ))
        if pc.attributes is None:
            return {
                    'offerCode': offer_file['offerCode'],
                    'product': product,
                    'term': terms
                }

        in_attribs = set(pc.attributes.items())
        attrib_items = set(product['attributes'].items())
        print("In: {0} Comp: {1}".format(in_attribs, attrib_items))
        print("Intersection: {0}".format(in_attribs <= attrib_items))
        if set(pc.attributes.items()) <= set(product['attributes'].items()):
            # any intersection means at least one matching Key and Value
            logger.debug('Attrib intersection found')
            return {
                'offerCode': offer_file['offerCode'],
                'product': product,
                'term': terms
            }
    except KeyError:
        logger.debug("SKU {0} filtered vs. Terms: {1}".format(
            sku, pc.terms))

    return None
