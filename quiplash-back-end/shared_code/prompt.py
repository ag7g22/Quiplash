import uuid
from azure.cosmos import ContainerProxy
from azure.core.exceptions import HttpResponseError
from shared_code.utils import utils

class InvalidTextError(ValueError):
    pass
class UnsupportedLanguageError(ValueError):
    pass
class NonExistingPlayerError(ValueError):
    pass

class prompt():
    """
    Stores temporary information about a single prompt.
    """
    utility = utils()

    # String List of languages
    supported_languages = ["en", "ga", "es", "hi", "zh-Hans", "pl"]

    # Constructor
    def __init__(self,player_proxy: ContainerProxy,trans_proxy: ContainerProxy,text,username):
        # auto generated unique id
        self.id = str(uuid.uuid4())
        self.PlayerContainerProxy = player_proxy
        self.TranslatorProxy = trans_proxy
        self.text = text
        self.username = username

        try:
            self.translation = self.TranslatorProxy.translate(body=[self.text], to_language=self.supported_languages)[0] # Get translations.
        except HttpResponseError as exception:
            if exception.error is not None:
                print(f"Error Code: {exception.error.code}")
                print(f"Message: {exception.error.message}")

    
    def is_valid(self):
        """
        Validation method to check if prompt is correctly written.
        """
        text = self.text

        # Check if there is a player username already stored
        username = self.username
        query = 'SELECT * FROM player WHERE CONTAINS(player.username, "{}")'.format(username)
        existing_username = self.utility.get_queryed_items(proxy=self.PlayerContainerProxy, query=query)
        if not existing_username:
            # If no existing username.
            raise NonExistingPlayerError("Player does not exist")
        
        # Check if the language is supported OR language confidence < 0.2
        if self.translation:
            detected = self.translation.detected_language
            if (detected["language"] not in self.supported_languages) or detected["score"] < 0.2:
                raise UnsupportedLanguageError("Unsupported language -> {0}, Confidence Score -> {1}".format(detected["language"], detected["score"]))

        # Check if the inital text is within the range of 20 to 100.
        if not (20 <= len(text) <= 100):
            raise InvalidTextError("Prompt less than 20 characters or more than 100 characters")

        return True
    
    def to_dict(self):
        """
        Uses the proxy to translate the appropriate languages and returns all supported translations in a dict.
        To 
        e.g.
        [   {"language": "en" , "text":"string"}, {"language": "es" , "text":"string translated to spanish"}, 
            {"language": "it" , "text": "string translated to italian"}, ...etc... ]
        """
        # Use the original text in the "texts" list.
        og_text = self.text
        detected_lan = self.translation.detected_language["language"]
        fst_entry = { "language": detected_lan, "text": og_text }

        new_prompt = {"id": self.id, "username": self.username, "texts": [fst_entry]}

        for translated_text in self.translation.translations:
            # Add the text in all available languages, but keep the original text!
            if translated_text.to != detected_lan:
                texts_entry = { "language": translated_text.to, "text": translated_text.text }
                new_prompt['texts'].append(texts_entry)

        return new_prompt

