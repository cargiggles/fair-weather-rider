"""
Fair Weather Rider Lambda v4.0
Andrew Cargill
2023-10-21 - Rewritten To Use Open Weather Map And Twilio
"""
import datetime as dt
from datetime import datetime
import os
from pyowm import OWM
import pytz
from pytz import timezone
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

# API Keys
open_weather_map_api_key = os.environ['open_weather_map_api_key']
twilio_account_sid = os.environ['twilio_account_sid']
twilio_auth_token = os.environ['twilio_auth_token']
twilio_messaging_service_sid = os.environ['twilio_messaging_service_sid']

# Constants
lat = float(os.environ['lat'])
lon = float(os.environ['lon'])

# User Preferences
lowest_acceptable_precip = float(os.environ['lowest_acceptable_precip'])
lowest_acceptable_temp = float(os.environ['lowest_acceptable_temp'])
to_phone = os.environ['to_phone']

# Local Time Zone To Be Populated By Open Weather Map API Call
local_time_zone = "" # America/Los_Angeles

bike_to_work = True

class BikeObject(object):
    """ An Hour Of The Day """
    def __init__(self, hour, precip, temp):
        self.hour = int(hour)
        self.precip = float(precip)
        self.temp = float(temp)

    def __str__(self):
        rep = str(self.hour) + ":00\n" + str(self.precip) + "% chance rain\n" + str(self.temp) + " F\n"
        return rep

    def bike_logic(self):
        global bike_to_work
        if self.precip > lowest_acceptable_precip or self.temp < lowest_acceptable_temp:
            bike_to_work = False

def open_weather_map_hourly_forecast(): # Replace With PyOWM
    """ Calls Open Weather Map API Using 'PyOWM' Module And Returns Forecast Object """
    exclude = "minutely,daily,alerts"
    units = "imperial"
    open_weather_map = OWM(open_weather_map_api_key)
    weather_manager = open_weather_map.weather_manager()
    forecast = weather_manager.one_call(lat=lat, lon=lon, exclude=exclude, units=units)
    return forecast

def get_local_date_time(hour):
    """ Accepts Unix Time Integer And Returns Date Time Object Converted To Local Time Zone """
    utc = pytz.utc
    utc_date_time = utc.localize(datetime.utcfromtimestamp(hour))
    local_time_zone_object = timezone(local_time_zone)
    local_date_time_object = utc_date_time.astimezone(local_time_zone_object)
    return local_date_time_object

def get_today_date_time():
    """ Returns Date Time Object Representing Today With Local Time Zone Offset """
    today_date_time = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(pytz.timezone(local_time_zone))
    return today_date_time

def send_sms(message): # Will Need to Update To Use Twilio
    """ Accepts String And Sends SMS To Phone Number At 6 AM Same Day"""
    client = Client(twilio_account_sid, twilio_auth_token)
    send_at = dt.datetime.today().astimezone(timezone(local_time_zone)).replace(hour=6, minute=0, second=0, microsecond=0).isoformat()
    try:
        message = client.messages.create(
            to=to_phone,
            from_=twilio_messaging_service_sid,
            body=message,
            schedule_type='fixed',
            send_at=send_at)
        print("SMS Message SID: " + message.sid)
    except TwilioRestException as error:
        print("Twilio Error: ")
        print(error)

def lambda_handler(event, context):
    global local_time_zone # Allows Change Made To "local_time_zone" To Be Viewable In All Other Functions

    # Open Weather Map Hourly API Call
    forecast = open_weather_map_hourly_forecast()

    # Set local_time_zone String
    local_time_zone = forecast.timezone

    # Slice Out Array Of Forecasts For Next 24 Hours
    hourly_forecasts = forecast.forecast_hourly[:24]

    # Make List Of Commute Forecast Objects
    commute_times = [7, 8, 9, 17, 18, 19] # Hours During Which I'd Conceivibly Be Biking
    commute_forecasts = []

    for hourly_forecast in hourly_forecasts:
        local_date_time = get_local_date_time(hourly_forecast.reference_time())

        if local_date_time.hour in commute_times:
            commute_forecasts.append(hourly_forecast)

    # Make List of Bike Objects - Representing Each Potential Hour Of Commute With Bike Logic
    bikes = []
    for commute_forecast in commute_forecasts:
        bike = BikeObject(get_local_date_time(commute_forecast.reference_time()).hour, commute_forecast.precipitation_probability, commute_forecast.temperature()['temp'])
        bikes.append(bike)

    # Invoke Each Bike Object's 'bike_logic()' Function To Test Whether To Toggle 'bike_to_work' False
    for bike in bikes:
        bike.bike_logic()
        print(bike)

    # Get Date Time Object Representing Today
    today_date_time = get_today_date_time()

    if bike_to_work:
        send_sms("Ride Your Bike!" + " " + "(" + today_date_time.strftime("%A") + ")")
        print(today_date_time.strftime("%a %b %d %Y") + "\nRide your bike!\nSMS Sent!")
    else:
        print("It's too cold and/or rainy, work from home.")
