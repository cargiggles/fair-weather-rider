# Fair Weather Rider Lambda v1.2
# Andrew Cargill
# May 11, 2018

import boto3
import datetime
import json
import os
import time
import urllib2

API_KEY = os.environ['API_KEY']
PHONE_NUMBER = os.environ['PHONE_NUMBER']
ZIP = os.environ['ZIP']
LOWEST_ACCEPTABLE_TEMP = int(os.environ['LOWEST_ACCEPTABLE_TEMP'])
CHANCE_RAIN = int(os.environ['CHANCE_RAIN'])

BIKE_TO_WORK = True

def lambda_handler(event, context):
    url = "http://api.wunderground.com/api/" + API_KEY + "/hourly/q/" + ZIP + ".json"
    response = urllib2.urlopen(url) # Calling Wunderground
    weather = json.load(response) # .json is read and put into the "weather" dictionary object

    today = datetime.datetime.now().day # int representing today's day of the month
    commuteTimes = [8, 9, 17, 18, 19] # hours during which I would conceivibly be commuting
    hours = [] # Empty list into which I'll place (up to) five "hour" objects

    class HourObject(object):
    	""" An Hour Of The Day """
    	def __init__(self, hour, pop, temp):
    		self.hour = int(hour)
    		self.pop = int(pop) # chance of precipitation
    		self.temp = int(temp)

    	def __str__(self):
    		rep = str(self.hour) + ":00\n" + str(self.pop) + "% chance rain\n" + str(self.temp) + " F\n"
    		return rep

    	def bike_logic(self):
    		global BIKE_TO_WORK
    		if self.pop > CHANCE_RAIN or self.temp < LOWEST_ACCEPTABLE_TEMP:
    			BIKE_TO_WORK = False

    def send_sns_sms():
        sns = boto3.client('sns')
        print sns.publish(PhoneNumber = PHONE_NUMBER, Message = "Ride Your Bike!" + " " + "(" + time.strftime("%a") + ")")
        # print both executes and records status codes to CloudWatch

    # MAIN

    for hour in weather['hourly_forecast']: # API returns 36 hour forecasts
    	if int(hour['FCTTIME']['hour']) in commuteTimes and int(hour['FCTTIME']['mday']) == today:
    		entry = HourObject(hour['FCTTIME']['hour'], hour['pop'], hour['temp']['english']) # Making object for each hour
    		hours.append(entry) # Adding hour object to list

    for each in hours:
    	each.bike_logic() # Invoke each hour object's function to test whether global BIKE_TO_WORK should be toggled off
    	print each

    if BIKE_TO_WORK == True:
    	send_sns_sms()
    	print time.strftime("%a %b %d") + "\nRide your bike!\nSMS Sent!"
    else:
    	print "It's too cold and/or rainy, bus it."
 
