from django.contrib import admin
from .models import *
admin.site.register(Course)
admin.site.register(Reminder)
admin.site.register(ReminderLog)
admin.site.register(UserProfile)
admin.site.register(UserCourse)
admin.site.register(CourseTemplate)
admin.site.register(AircraftManufacturer)
admin.site.register(AircraftModelGroup)
admin.site.register(AircraftScrapingSession)
admin.site.register(Aircraft)
admin.site.register(OpenTask)
admin.site.register(OpenWorkPackage)
admin.site.register(AircraftAlert)
admin.site.register(AircraftFlightSchedule)


