# -*- coding: utf-8 -*-
import scrapy
import json
import re
import requests

with open("C:/Users/Sam/AppData/Local/Programs/Python/Python36/depop/depop/tags.json") as f:
    tags = json.load(f)


class SolditemsSpider(scrapy.Spider):
    name = 'soldItems'
    allowed_domains = ['depop.com', 'webapi.depop.com']
    start_urls = ['https://www.depop.com/ollyt155/']

    def __init__(self):
        self.urls = ['https://www.depop.com/ollyt155/']
        self.currentID = None
        self.itemsCollected = 0
        self.profilesCollected = 0

        self.rowsInserted = 0;
        self.rowsUpdated = 0;

        try:
            with open("sold.json") as f:
                self.results = json.load(f)
        except:
            self.results = {}

    def parse(self, response):


        # Gets the meta data from the bottom of the page
        meta = json.loads(response.css("script#__NEXT_DATA__::text").get())

        # Get user id from within the meta
        id = meta['props']['pageProps']['shop']['id']
        username = meta['props']['pageProps']['shop']['username']

        #print("Current Profile = {}".format(username))
        #print("Total profiles collected: {}".format(self.profilesCollected))
        #print("Total profiles scanned: {}".format(self.itemsCollected))
        self.currentID = id

        # Get the URL of the API that returns following
        url = "https://webapi.depop.com/api/v1/user/{}/followers/".format(str(id))

        # Grab user link from lists of following
        yield scrapy.Request(url, callback=self.getFollowerLinks)

        #print("Scanned profile {}".format(self.currentID))


        #if len(self.urls) > 0:
            #yield response.follow(self.url.pop(), callback = self.parse)



    def getFollowerLinks(self, response):
        #print(" ... enqueueing profile connections")
        jsonresponse = json.loads(response.body_as_unicode())
        for item in jsonresponse['objects']:
            username = item['username']
            profileLink = "https://www.depop.com/{}/".format(username)
            url = "https://webapi.depop.com/api/v1/shop/{}/products?limit=200".format(str(self.currentID))
            self.profilesCollected += 1
            yield scrapy.Request(url, callback=self.getItemLinks)
            #if profileLink not in self.urls:
            #    self.urls.append(profileLink)
            #print(len(self.urls))
            yield scrapy.Request(profileLink, callback=self.parse)


        url = "https://webapi.depop.com/api/v1/shop/{}/products?limit=200".format(str(self.currentID))
        yield scrapy.Request(url, callback=self.getItemLinks)

    def getItemLinks(self, response):
        self.itemsCollected += 1
        #print(" ... iterating through items on page")
        jsonresponse = json.loads(response.body_as_unicode())
        for item in jsonresponse['products']:
            price = item['price']

            # Only scan products in GBP and that are sold
            if price['currency_name'] == 'GBP':
                # Get URL of sold item
                url_item = "https://www.depop.com/products/" + item['slug'] + "/"

                # Scan that page
                yield scrapy.Request(url_item, callback=self.addItem)

    def addItem(self, response):
        # Gets the meta data from the bottom of the page
        meta = json.loads(response.css("script#__NEXT_DATA__::text").get())

        output = {}

        # PROPERTIES
        try:
            id = meta['props']['initialReduxState']['product']['product']['id']
        except KeyError:
            pass
        else:
            output['id'] = id

            # Get item link
            slug = meta['props']['initialReduxState']['product']['product']['slug']
            username = meta['props']['initialReduxState']['product']['product']['seller']['username']
            item_link = 'https://www.depop.com/products/{}/'.format(slug)
            output['item_link'] = item_link

            currency_symbol = meta['props']['initialReduxState']['product']['product']['price']['currency_symbol']
            output['currency_symbol'] = currency_symbol

            price_amount = meta['props']['initialReduxState']['product']['product']['price']['price_amount']
            output['price_amount'] = price_amount


            shipping_cost = meta['props']['initialReduxState']['product']['product']['price']['national_shipping_cost']
            output['shipping_cost'] = shipping_cost

            date_updated = meta['props']['initialReduxState']['product']['product']['date_updated']
            output['date_updated'] = date_updated

            description = meta['props']['initialReduxState']['product']['product']['description']
            output['description'] = description

            try:
                image_url = [meta['props']['initialReduxState']['product']['product']['pictures'][0][0]['url']][0]
            except IndexError:
                image_url = None
            output['image_url'] = image_url

            # Sold Status
            sale_status = meta['props']['initialReduxState']['product']['product']['status']
            print(sale_status)
            output['sold'] = sale_status

            # VISUALS
            descAttr = getAttr(format(description), tags)
            colour = descAttr['colour']
            #self.results[id]['colour'] = colour
            output['colour'] = colour

            brand = descAttr['brand']
            #self.results[id]['brand'] = brand
            output['brand'] = brand

            gender = descAttr['gender']
            #self.results[id]['gender'] = gender
            output['gender'] = gender

            style = descAttr['style']
            #self.results[id]['style'] = style
            output['style'] = style

            size = descAttr['size']
            #self.results[id]['size'] = size
            output['size'] = size



            # SAVE RESULTS
            url = 'http://localhost/saveItem.php'
            post_data = output

            x = requests.post(url, data=post_data)

            if x.text == 'Row inserted':
                self.rowsInserted += 1
            elif x.text == 'Row updated':
                self.rowsUpdated += 1

            print("\n\"{}\"\nInserted: {}\nUpdated: {}\n".format(x.text, self.rowsInserted, self.rowsUpdated))

            yield None

def getAttr(desc, tags):
    attributes = {}
    for attr in tags:
        most_common_tag = None;
        most_occurences = 0
        for tag in tags[attr]:
            count = sum(1 for _ in re.finditer(r'\b%s\b' % re.escape(tag), desc))
            # print("TAG: {}\nCOUNT: {}\n".format(tag, count))
            if count > most_occurences:
                most_common_tag = tags[attr][tag]
                most_occurences = count
        if most_common_tag is None:
            pass
            # print("{} = None\n Original Desc: \"{}\"\n Formatted Desc: \"{}\"\n".format(attr, repr(org), desc))
        attributes[attr[:-1]] = most_common_tag
    return attributes


def format(text):
    output = ""
    text = text.replace("\n", " ")
    text.replace("/", " ")
    for letter in text:
        if re.search("[a-z]|[A-Z]|[0-9]|[' ']", letter):
            output += letter.upper()
    return output
