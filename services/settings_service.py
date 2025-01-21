from models import AppSettings

class SettingsService:
    @staticmethod
    def get_setting(key):
        setting = AppSettings.query.filter_by(key=key).first()
        return setting.value if setting else None
    
    @staticmethod
    def get_settings_by_category(category):
        settings = AppSettings.query.filter_by(category=category).all()
        return {s.key: s.value for s in settings}