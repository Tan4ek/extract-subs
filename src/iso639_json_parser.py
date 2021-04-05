import json

from iso639 import languages


class Iso639Encoder(json.JSONEncoder):
    _iso639_type = type(list(languages)[0])

    def default(self, obj):
        if isinstance(obj, self._iso639_type):
            return {
                "_type": "iso639_3_lang",
                "value": obj.part3
            }
        return super(Iso639Encoder, self).default(obj)


class Iso639Decoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        if '_type' not in obj:
            return obj
        if obj['_type'] == 'iso639_3_lang' and 'value' in obj:
            return languages.get(part3=obj['value'])
        return obj
