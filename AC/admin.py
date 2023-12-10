from django.contrib import admin
# from .models import Scheduler
from .models import ServingQueue, WaitingQueue, Server, Scheduler, Room
# Register your models here.


"""用于配置Django管理界面来管理数据"""

class RoomAdmin(admin.ModelAdmin):
    list_display = ['request_time', 'room_id', 'current_temp', 'target_temp', 'fan_speed', 'fee']


# 将五个模型注册到管理界面
admin.site.register(Scheduler)
admin.site.register(ServingQueue)
admin.site.register(WaitingQueue)
admin.site.register(Server)
admin.site.register(Room, RoomAdmin)

