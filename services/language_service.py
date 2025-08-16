# Multi-language Support Service

try:
    from translate import Translator
except ImportError:
    Translator = None

class LanguageService:
    def translate(self, text, lang):
        if Translator:
            translator = Translator(to_lang=lang)
            try:
                return translator.translate(text)
            except Exception as e:
                return f"Translation error: {str(e)}"
        else:
            return f"Translation package not installed. Please run 'pip install translate'."
