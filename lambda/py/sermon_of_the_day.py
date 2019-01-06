import logging
from datetime import datetime
import calendar
import pytz
import requests
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.utils import is_request_type, is_intent_name
from alexa import util

sb = SkillBuilder()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
API_URL = "https://api.desiringgod.org/"
ICON_URL = "https://s3.amazonaws.com/alexaskillresourcesabarranc/icon_sermon_of_the_day.png"


@sb.request_handler(can_handle_func=is_request_type("LaunchRequest"))
def launch_request_handler(handler_input):
    """
    Launch request
    :param handler_input: from the alexa skill
    :return: Response object with speech and audio and APL
    """
    # Calculation of page number for DG API, leap year and current date effects index of page
    try:
        context = handler_input.request_envelope.to_dict()['context']
        device_id = context['system']['device']['device_id']
        api_access_token = context['system']['api_access_token']
        settings_api_url = 'https://api.amazonalexa.com'
        r = requests.get(settings_api_url + '/v2/devices/' + device_id + '/settings/System.timeZone', headers={
            'Authorization': 'Bearer ' + api_access_token})
        zone = r.text
        now = datetime.now(pytz.timezone(zone.replace('"', '')))
    except Exception as err:
        now = datetime.now(pytz.timezone('America/New_York'))
        logging.error('Could\'nt get user time zone error:{0}'.format(str(err)))
    is_leap_year = calendar.isleap(now.year)
    if is_leap_year or now < pytz.UTC.localize(datetime.strptime(
            '02-27-' + str(now.year) + ' 23:59:59.99', '%m-%d-%Y %H:%M:%S.%f'), now):
        index = now.timetuple().tm_yday
    else:
        index = now.timetuple().tm_yday + 1
    # Get information using index from DG API
    data = get_sermon_of_the_day(index)
    speech_text = "Playing Sermon of the day from Desiring God, titled: " + data['title']
    response = util.play(url=data['sound_url'],
                         offset=0,
                         text=speech_text,
                         data={'title': data['title'],
                               'subtitle': 'Desiring God',
                               'icon_url': ICON_URL},
                         response_builder=handler_input.response_builder)
    logging.error(response)
    return response


@sb.request_handler(can_handle_func=is_intent_name("AMAZON.HelpIntent"))
def help_intent_handler(handler_input):
    """
    Launch request
    :param handler_input: from the alexa skill
    :return: Response object with speech and audio and APL
    """
    speech_text = "You can play, pause and start over the sermon."

    return handler_input.response_builder.speak(speech_text).ask(
        speech_text).response


@sb.request_handler(
    can_handle_func=lambda handler_input:
        is_intent_name("AMAZON.CancelIntent")(handler_input) or
        is_intent_name("AMAZON.StopIntent")(handler_input))
def cancel_and_stop_intent_handler(handler_input):
    """Single handler for Cancel and Stop Intent."""
    speech_text = "Goodbye"
    return handler_input.response_builder.speak(speech_text).response


@sb.request_handler(can_handle_func=is_intent_name("AMAZON.FallbackIntent"))
def fallback_handler(handler_input):
    """AMAZON.FallbackIntent is only available in en-US locale.
    This handler will not be triggered except in that locale,
    so it is safe to deploy on any locale.
    """
    speech = (
        "The Sermon of the day skill can't help you with that."
        "You can say play, pause, resume, start over, stop or exit.")
    reprompt = "What would you like to do?"
    handler_input.response_builder.speak(speech).ask(reprompt)
    return handler_input.response_builder.response


@sb.request_handler(can_handle_func=is_request_type("SessionEndedRequest"))
def session_ended_request_handler(handler_input):
    """Handler for Session End."""
    return handler_input.response_builder.response


@sb.exception_handler(can_handle_func=lambda i, e: True)
def all_exception_handler(handler_input, exception):
    """Catch all exception handler, log exception and
    respond with custom message.
    """
    logger.error(exception, exc_info=True)

    speech = "Sorry, there was some problem. Please try again!"
    handler_input.response_builder.speak(speech).ask(speech)

    return handler_input.response_builder.response


def get_sermon_of_the_day(index):
    """
    Gets a tuple info on the sermon of the day
    :param index: integer of day of year that will be retrieved
    :return: gets sermon of the day information as tuple for deconstructing, sound_url, title, and scriptural_ref
    """
    url = API_URL + '/v0/collections/wjfmvjzo/resources?page[size]=1&page[number]=' + str(index)
    r = requests.get(url, headers={'Authorization': 'Token token="e6f600e7ee34870d05a55b28bc7e4a91"'})
    if r.status_code != 200:
        raise Exception('Could not access Desiring God\'s API.')
    data = r.json()
    sound_url = data['data'][0]['attributes']['audio_stream_url']
    title = data['data'][0]['attributes']['title']
    scriptural_ref = data['data'][0]['attributes']['scripture_references']
    if len(scriptural_ref) == 0:
        scriptural_ref = 'No specific Scripture Noted.'
    elif len(scriptural_ref) > 1:
        scriptural_ref = ', '.join(scriptural_ref)
    else:
        scriptural_ref = scriptural_ref[0]
    return {'sound_url': sound_url, 'title': title, 'scriptural_ref': scriptural_ref}


handler = sb.lambda_handler()
