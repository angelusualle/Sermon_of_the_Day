from ask_sdk.standard import StandardSkillBuilder
import logging
from datetime import datetime
import calendar
import pytz
import requests
from ask_sdk_core.utils import is_request_type, is_intent_name
from alexa import util

sb = StandardSkillBuilder(
    table_name='Sermon_of_the_day_skill_play_data', auto_create_table=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
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
    apl_enabled = \
        handler_input.request_envelope.context.system.device.supported_interfaces.alexa_presentation_apl is not None
    speech_text = "Playing Sermon of the day from Desiring God, titled: " + data['title']
    data_sources = {
                            "bodyTemplate3Data": {
                                "type": "object",
                                "objectId": "bt3Sample",
                                "textContent": {
                                    "title": {
                                        "type": "PlainText",
                                        "text": data['title']
                                    },
                                    "scripturalRef": {
                                        "type": "PlainText",
                                        "text": data['scriptural_ref']
                                    }
                                },
                                "hintText": "Try, \"Alexa, start over.\""
                            }}
    info = {'title': data['title'],
                               'subtitle': 'Desiring God',
                               'icon_url': ICON_URL}
    response = util.play(url=data['sound_url'],
                         offset=0,
                         text=speech_text,
                         data=info,
                         response_builder=handler_input.response_builder,
                         document='alexa/APLTemplate.json',
                         datasources=data_sources,
                         apl_enabled=apl_enabled)
    # Persistance atributes to make playback requests easier and faster
    persistence_attr = handler_input.attributes_manager.persistent_attributes
    persistence_attr['url'] = data['sound_url']
    persistence_attr['data'] = info
    persistence_attr['document'] = 'alexa/APLTemplate.json'
    persistence_attr['datasources'] = data_sources
    persistence_attr['apl_enabled'] = apl_enabled
    return response


@sb.request_handler(can_handle_func=is_intent_name("AMAZON.PauseIntent"))
def pause_request_handler(handler_input):
    speech_text = 'Pausing sermon'
    return util.stop(speech_text, handler_input.response_builder)


@sb.request_handler(can_handle_func=is_intent_name("AMAZON.ResumeIntent"))
def resume_request_handler(handler_input):
    speech_text = 'Resuming sermon'
    return util.resume(speech_text, handler_input)


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
        is_intent_name("AMAZON.NextIntent")(handler_input) or
        is_intent_name("AMAZON.PreviousIntent")(handler_input))
def next_or_previous_handler(handler_input):
    return handler_input.response_builder.speak(
        'Can\'t do that, this skill only plays today\'s sermon').response


@sb.request_handler(
    can_handle_func=lambda handler_input:
        is_intent_name("AMAZON.CancelIntent")(handler_input) or
        is_intent_name("AMAZON.StopIntent")(handler_input))
def cancel_and_stop_intent_handler(handler_input):
    """Single handler for Cancel and Stop Intent."""
    speech_text = "Goodbye"
    return util.stop(speech_text, handler_input.response_builder)


@sb.request_handler(can_handle_func=is_intent_name("AMAZON.FallbackIntent"))
def fallback_handler(handler_input):
    """AMAZON.FallbackIntent is only available in en-US locale.
    This handler will not be triggered except in that locale,
    so it is safe to deploy on any locale.
    """
    speech = (
        "The Sermon of the day skill can't help you with that."
        "You can say play, pause, resume, start over, stop or cancel.")
    handler_input.response_builder.speak(speech)
    return handler_input.response_builder.response


@sb.request_handler(can_handle_func=is_request_type("SessionEndedRequest"))
def session_ended_request_handler(handler_input):
    """Handler for Session End."""
    return handler_input.response_builder.response


@sb.request_handler(can_handle_func=is_request_type("AudioPlayer.PlaybackStarted"))
def playback_started_handler(handler_input):
    """Handler for Session End."""
    logger.info("In Playback started")
    return handler_input.response_builder.response


@sb.request_handler(can_handle_func=is_request_type("AudioPlayer.PlaybackStopped"))
def playback_stopped_handler(handler_input):
    """Handler for Session End."""
    persistence_attr = handler_input.attributes_manager.persistent_attributes
    persistence_attr['playback_info']['offset_in_ms'] = handler_input.request_envelope.request.to_dict()['offset_in_ms']
    logger.info("In PlaybackStopped")

    return handler_input.response_builder.response


@sb.request_handler(can_handle_func=is_request_type("AudioPlayer.PlaybackEnded"))
def playback_ended_handler(handler_input):
    """Handler for Session End."""
    logger.info("In PlaybackEnded")
    return handler_input.response_builder.response


@sb.exception_handler(can_handle_func=lambda i, e: True)
def all_exception_handler(handler_input, exception):
    """Catch all exception handler, log exception and
    respond with custom message.
    """
    logger.error(exception, exc_info=True)
    speech = "Sorry, a problem has occurred. Please try again later."
    handler_input.response_builder.speak(speech).response

    return handler_input.response_builder.response


@sb.global_request_interceptor()
def process_request(handler_input):
    """Log the alexa requests."""
    logger.debug("Alexa Request: {}".format(
        handler_input.request_envelope.request))


@sb.global_response_interceptor()
def process_response(handler_input, response):
    logger.debug("Alexa Response: {}".format(response))


@sb.global_request_interceptor()
def process_request_persist(handler_input):
    """Check if user is invoking skill for first time and initialize preset."""
    persistence_attr = handler_input.attributes_manager.persistent_attributes

    if len(persistence_attr) == 0:
        persistence_attr["playback_info"] = {
            "offset_in_ms": 0
        }
    else:
        # Convert decimals to integers, because of AWS SDK DynamoDB issue
        # https://github.com/boto/boto3/issues/369
        playback_info = persistence_attr.get("playback_info")
        playback_info["offset_in_ms"] = int(playback_info.get(
            "offset_in_ms"))


@sb.global_response_interceptor()
def process_response(handler_input, response):
    handler_input.attributes_manager.save_persistent_attributes()


def get_sermon_of_the_day(index):
    """
    Gets a dictionary with info on the sermon of the day
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
