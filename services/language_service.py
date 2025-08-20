import re

class LanguageService:
    def extract_intent_and_args(self, text):
        """
        Extracts intent and arguments from a user message for command routing.
        Returns a dict: {"intent": ..., "args": {...}}
        """
        text_l = text.lower().strip()
        args = {}
        # Simple intent mapping
        if text_l.startswith("!repos") or "list repos" in text_l or "show repos" in text_l or "repositories" in text_l:
            return {"intent": "show_repos", "args": {}}
        if text_l.startswith("!status") or "status" in text_l:
            return {"intent": "show_status", "args": {}}
        if text_l.startswith("!ideas") or "ideas" in text_l:
            return {"intent": "show_ideas", "args": {}}
        if text_l.startswith("!help") or text_l.startswith("!guide") or "help" in text_l or "guide" in text_l:
            return {"intent": "guide_cmd", "args": {}}
        # Start working on repo
        match = re.search(r"start working on (the )?([\w\- ]+)( repository| repo)?", text_l)
        if match:
            repo = match.group(2).strip()
            args["repo"] = repo
            return {"intent": "start_work_on_repo", "args": args}
        # Create repo
        match = re.search(r"create (a )?(repo|repository) ([\w\- ]+)", text_l)
        if match:
            repo = match.group(3).strip()
            args["repo"] = repo
            return {"intent": "create_repository", "args": args}
        # Delete repo
        match = re.search(r"delete (the )?(repo|repository) ([\w\- ]+)", text_l)
        if match:
            repo = match.group(3).strip()
            args["repo"] = repo
            return {"intent": "delete_repository", "args": args}
        # Fallback: treat as query
        return {"intent": None, "args": {}}
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
