from django.db import models
from django.utils import timezone
import threading
import django
from django.http import HttpResponse
import csv
from django.core.exceptions import ObjectDoesNotExist
import datetime
from django.db.models import Q
import os

detail = []
for _ in range(6):
    detail.append({'序号':[], '房间号':[], '服务开始时间':[], '请求时间':[], '服务时长':[], '风速':[],
                   '当前费用':[], '费率':[], '操作类型':[]
                   #, '服务结束时间':[]
                   })
detailnum = [1]*5
BeginTime = [-1]*5

# 下面这个网站提供了详细的字段类型参考，请大家仔细比较，选择最优字段类型。
# note: https://docs.djangoproject.com/zh-hans/2.2/ref/models/fields/#field-types


class ServingQueue(models.Model):
    """
    正在服务的队列，存放所有正在服务的房间对象
    """
    # 在调度队列中的房间对象
    # 注：不确定这么写好不好，我觉得serve_time应该和房间对象绑定在一起可能会好一点。
    # 如果有更好的类型，请替换。
    room_list = []#存储正在服务的对象

    serving_num = models.IntegerField(verbose_name='服务对象数', default=0)

    def __init__(self):
        super().__init__()
        self.serving_num = 0



    def insert(self, room):
        "向调度队列中插入一个房间"
        room.state = 1
        room.scheduling_num += 1
        self.room_list.append(room)
        # 当风速相同，按服务时间降序排列，即服务时间长的排前面
        self.room_list.sort(key=lambda x: (-x.fan_speed, -x.serve_time))
        self.serving_num += 1
        BeginTime[room.room_id - 1] = timezone.now()
        return True

    #  修改温度
    def set_target_temp(self, room_id, target_temp):
        "修改特定房间的目标温度"
        for room in self.room_list:
            if room.room_id == room_id:
                room.target_temp = target_temp
                break
        return True

    #  修改风速
    def set_fan_speed(self, room_id, fan_speed, fee_rate):
        "修改特定房间的风速"
        for room in self.room_list:
            if room.room_id == room_id:
                room.fan_speed = fan_speed
                room.fee_rate = fee_rate
                # 当风速相同，按服务时间降序排列，即服务时间长的排前面
                self.room_list.sort(key=lambda x: (-x.fan_speed, -x.serve_time))
                break
        return True

    def delete_room(self, room):
        """
        从调度队列删除对应的房间
        param： room
        """
        self.room_list.remove(room)
        self.serving_num -= 1
        return True

    def update_serve_time(self):
        "更新服务队列中每个房间的服务时间"
        if self.serving_num != 0:
            for room in self.room_list:
                room.serve_time += 1 #单位是min
        timer = threading.Timer(5, self.update_serve_time)  # 每1min执行一次函数
        timer.start()

    def auto_fee_temp(self, mode):
        #print(mode)

        """
        根据风速和模式（制热或制冷）自动计算费用和调整温度
        回温和计费函数，设定风速H:1元/min,即0.016元/s,回温2℃/min，即0.03℃/s
        M:0.5元/min,即0.008元/s,回温1.5℃/min，即0.025℃/s
        L:0.3元/min,即0.005元/s,回温1℃/min，即0.016℃/s
        mode=1,制热
        mode=2,制冷
        :return:
        """
        if mode == 1:
            for room in self.room_list:
                if room.fan_speed == 1:
                    room.fee += 0.016*6
                    room.current_temp += 0.016*6#0.03
                elif room.fan_speed == 2:
                    room.fee += 0.008*6
                    room.current_temp += 0.016*6#0.025
                else:
                    room.fee += 0.005*6
                    room.current_temp += 0.016*6
            timer = threading.Timer(1, self.auto_fee_temp, [1])  # 每1秒执行一次函数
            timer.start()
        else:
            for room in self.room_list:
                if room.fan_speed == 1:
                    room.fee += 0.016*6
                    room.current_temp -= 0.016*6#0.03
                elif room.fan_speed == 2*6:
                    room.fee += 0.008*6
                    room.current_temp -= 0.016*6#0.025
                else:
                    room.fee += 0.005*6
                    room.current_temp -= 0.016*6
            timer = threading.Timer(1, self.auto_fee_temp, [2])  # 每1秒执行一次函数
            timer.start()


class WaitingQueue(models.Model):
    """
    等待队列，存放所有等待服务的房间对象
    """
    room_list = []

    waiting_num = models.IntegerField(verbose_name='等待对象数', default=0)

    def __init__(self):
        super().__init__()
        self.waiting_num = 0

    def set_target_temp(self, room_id, target_temp):
        for room in self.room_list:
            if room.room_id == room_id:
                room.target_temp = target_temp
                break
        return True

    def set_fan_speed(self, room_id, fan_speed, fee_rate):
        for room in self.room_list:
            if room.room_id == room_id:
                room.fan_speed = fan_speed
                room.fee_rate = fee_rate
                break
        self.room_list.sort(key=lambda x: (x.fan_speed))
        return True

    def delete_room(self, room):
        """
        从等待队列删除对应的房间
        :param room:
        :return:
        """
        self.room_list.remove(room)
        self.waiting_num -= 1
        return True

    #   参数用room对象更好，
    def insert(self, room):
        if not detail[room.room_id]['操作类型'] or detail[room.room_id]['操作类型'][-1] != '资源调度': 
            #if not detail[room.room_id]['操作类型'] or abs(detail[room.room_id]['请求时间'][-1] != timezone.now()) < 0.2:


                ###以下是我添加的###
                Speed = ('', '高速', '中速', '低速')
                room_id = room.room_id
                detail[room_id]['序号'].append(detailnum[room_id - 1])
                detailnum[room_id - 1] += 1
                detail[room_id]['房间号'].append(room_id)
                # detail[room_id]['请求时间'].append
                # detail[room_id]['服务开始时间'].append
                detail[room_id]['请求时间'].append(timezone.now())
                # detail[room_id]['服务时长'].append
                detail[room_id]['风速'].append(Speed[room.fan_speed])
                detail[room_id]['当前费用'].append(room.fee)
                detail[room_id]['费率'].append(room.fee_rate)
                detail[room_id]['操作类型'].append('资源调度')
                detail[room_id]['服务开始时间'].append(BeginTime[room_id - 1])
                BeginTime[room_id - 1] = -1

        
        room.state = 2
        room.scheduling_num += 1
        self.room_list.append(room)
        self.waiting_num += 1
        self.room_list.sort(key=lambda x: (x.fan_speed))

        return True

    def update_wait_time(self):
        if self.waiting_num != 0:
            for room in self.room_list:
                room.wait_time += 1
        timer = threading.Timer(5, self.update_wait_time)  # 每1min执行一次函数
        timer.start()


class Scheduler(models.Model):
    """
    名称：调度器/中控机
    作用：作为温控系统的中心，为到来的请求分配服务对象，提供计费功能
    """

    STATE_CHOICE = [
        (1, 'WORKING'),
        (2, 'SHUTDOWN'),
        (3, 'SETMODE'),
        (4, 'READY')
    ]

    #缺省的目标温度
    TEMP_CHOICE = [
        (22, "制热"),
        (25, "制冷")
    ]
    # 第一次发出开机请求的房间数
    request_num = 0

    # 房间请求数，详单中的主键
    request_id = 0

    # 中控机所处的状态
    state = models.IntegerField(verbose_name='中控机状态', choices=STATE_CHOICE, default=2)

    # 最高温度限制
    temp_high_limit = models.IntegerField(verbose_name='最高温度限制', default=25)#0

    # 最低温度限制
    temp_low_limit = models.IntegerField(verbose_name="最低温度限制", default=18)#0

    # 缺省目标温度
    default_target_temp = models.IntegerField(verbose_name="默认目标温度", choices=TEMP_CHOICE, default=22)



    # 高风速时的费率
    fee_rate_h = models.FloatField(verbose_name="高风速费率", default=1.0)

    # 低风速时的费率
    fee_rate_l = models.FloatField(verbose_name="低风速费率", default=0.3333)

    # 中风速时的费率
    fee_rate_m = models.FloatField(verbose_name="中风速费率", default=0.5)#11

    #  等待队列
    WQ = WaitingQueue()

    #  服务队列
    SQ = ServingQueue()

    #  存储5个房间,房间开始时的状态都是3--“SHUTDOWN”关机状态
    rooms = []

    MODE_CHOICE = [
        (1, '制热'),
        (2, '制冷')
    ]
    mode = models.IntegerField(verbose_name='工作模式', choices=MODE_CHOICE, default=1)  # 默认为制冷

    def power_on(self):
        """
        开启中控机，中控机状态修改为”SETMODE“
        初始化房间队列
        :return:
        """
        Room.objects.all().delete()
        self.state = 3
        #  只要服务队列有房间就计费和计温,制热mode=1,制冷mode=2,
        if self.mode == 1:
            self.SQ.auto_fee_temp(1)
        else:
            self.SQ.auto_fee_temp(2)

        # 开启调度函数
        self.scheduling()
        #  只要有服务就检查是否有房间达到目标温度
        self.check_target_arrive()
        # 开启调度队列和等待队列的计时功能
        self.SQ.update_serve_time()
        self.WQ.update_wait_time()

        return self.state

    # def change_room_mode(self, room_id, mode):
    #     for room in self.rooms:
    #         if room.room_id == room_id:
    #             room.mode = mode

    def set_init_temp(self, room_id, init_temp,mode=None):
        """
        设置房间的初始温度
        :param room_id:
        :param init_temp:
        :return:
        """
        for room in self.rooms:
            if room.room_id == room_id:
                #room.mode = mode
                room.init_temp = init_temp

    def request_on(self, room_id, current_room_temp):
        """
        一个请求到来，第一次开机分配房间对象然后处理，否则直接处理
        调用调度算法
        问题：房间ID如何分配的
        开始计费和计温
        :param room_id:
        :param current_room_temp:
        :return:
        """
        return_room = Room(request_id=self.request_id)#创建一个新的房间实例
        flag = 1#用于跟踪房间是否是第一次请求服务
        for room in self.rooms:
            if room.room_id == room_id:  # 不是第一次开机，直接处理
                #room.current_temp = current_room_temp
                flag = 0
                if self.SQ.serving_num < 3:  # 服务队列未满
                    self.SQ.insert(room)
                else:  # 服务队列已满
                    self.WQ.insert(room)

                return_room = room
                #  写入数据库
                room.request_time = timezone.now()
                room.request_id = self.request_id
                self.request_id += 1
                room.operation = 3
                room.save(force_insert=True)
        if flag == 1:  # 是第一次开机，先分配房间对象再处理
            temp_room = return_room
            self.request_num += 1  # 发出第一次开机请求的房间数加一
            if self.request_num > 5:  # 控制只能有五个房间开机
                return False  # 返回

            temp_room.room_id = room_id
            temp_room.current_temp = current_room_temp
            self.rooms.append(temp_room)
            if self.SQ.serving_num < 3:  # 服务队列未满
                self.SQ.insert(temp_room)
            else:  # 服务队列已满
                self.WQ.insert(temp_room)

            return_room = temp_room
            #  写入数据库
            temp_room.request_time = timezone.now()
            self.request_id += 1
            temp_room.operation = 3
            temp_room.save(force_insert=True)

        return return_room  # 返回房间的状态，目标温度，风速，费率以及费用

    def set_service_num(self, service_num):
        """
        :param service_num:
        :return:
        """
        self.service_num = service_num

    def change_target_temp(self, room_id, target_temp):
        """
        修改目标温度
        :param room_id:
        :param target_temp:
        :return:


        """
        if target_temp < 18:
            target_temp = 18
        if target_temp > 25:
            target_temp = 25


        for room in self.rooms:#?
            if room.room_id == room_id:
                if room.state == 1:  # 在调度队列中
                    self.SQ.set_target_temp(room_id, target_temp)
                elif room.state == 2:  # 在等待队列中
                    self.WQ.set_target_temp(room_id, target_temp)
                else: room.target_temp = target_temp

                # 写入数据库
                room.request_id = self.request_id
                self.request_id += 1
                room.operation = 1
                room.request_time = timezone.now()
                room.save(force_insert=True)

                return room

    def change_fan_speed(self, room_id, fan_speed):
        """
        处理调风请求
        :param room_id:
        :param fan_speed:
        :return:
        """
        if fan_speed == 1:
            fee_rate = self.fee_rate_h  # 高风速时的费率
        elif fan_speed == 2:
            fee_rate = self.fee_rate_m  # 中风速时的费率
        elif fan_speed < 1:
            fee_rate = self.fee_rate_h
        else:
            fee_rate = self.fee_rate_l  # 低风速时的费率
        for room in self.rooms:
            if room.room_id == room_id:
                Speed = ('', '高速', '中速', '低速')
                detail[room_id]['风速'].append(Speed[room.fan_speed])
                detail[room_id]['费率'].append(room.fee_rate)
                detail[room_id]['服务开始时间'].append(BeginTime[room_id - 1])
                if room.state == 1:
                    BeginTime[room_id - 1] = timezone.now()

                if room.state == 1:  # 在调度队列中
                    self.SQ.set_fan_speed(room_id, fan_speed, fee_rate)
                elif room.state == 2:  # 在等待队列中
                    self.WQ.set_fan_speed(room_id, fan_speed, fee_rate)
                else:
                    room.fan_speed = fan_speed
                    room.fee_rate = fee_rate
                # 写入数据库
                room.request_id = self.request_id
                self.request_id += 1
                room.operation = 2
                room.request_time = timezone.now()
                room.save(force_insert=True)
                detail[room_id]['序号'].append(detailnum[room_id - 1])
                detailnum[room_id - 1] += 1
                detail[room_id]['房间号'].append(room_id)
                # detail[room_id]['请求时间'].append
                # detail[room_id]['服务开始时间'].append
                detail[room_id]['请求时间'].append(room.request_time)
                # detail[room_id]['服务时长'].append
                detail[room_id]['当前费用'].append(room.fee)
                detail[room_id]['操作类型'].append('修改风速')

                return room

    def check_room_state(self):
        """
        每5s查看一次房间状态
        :return:
        """
        timer = threading.Timer(2, self.check_room_state)  # 每五秒执行一次check函数,list_room为参数
        timer.start()
        return self.rooms

    def update_room_state(self, room_id):
        """
        每分钟查看一次房间状态
        :param room_id:
        :return:
        """
        for room in self.rooms:
            # print(room.room_id)
            if room.room_id == room_id:
                return room

    def set_para(self, temp_high_limit, temp_low_limit, default_target_temp, fee_rate_h, fee_rate_l, fee_rate_m,mode):
        """
        设置中控机参数
        :param temp_high_limit:
        :param temp_low_limit:
        :param default_target_temp:
        :param fee_rate_h:
        :param fee_rate_l:
        :param fee_rate_m:
        :return:
        """
        print(timezone.now())
        self.temp_high_limit = temp_high_limit
        self.temp_low_limit = temp_low_limit
        self.default_target_temp = default_target_temp
        self.fee_rate_h = fee_rate_h
        self.fee_rate_l = fee_rate_l
        self.fee_rate_m = fee_rate_m
        #self.mode=mode

        if mode=='hot':
            self.mode=1
        else:
            self.mode=2

        return True

    def start_up(self):
        """
        参数设置完毕，进入READY状态
        :return:
        """
        self.state = 4
        return self.state

    def request_off(self, room_id):
        """
         # 处理房间的关机请求(未开机时，不能发出关机请求)
         # 假定，房间关机，房间温度每分钟变化0.5度，直到房间的初始化温度
        :param room_id:
        :return:
        """
        for room in self.rooms:
            if room.room_id == room_id:
                #room.current_temp = room.init_temp
                self.cool_down_temp(room)
                #  关机回到初始温度
                if room.state == 1:  # 在调度队列中
                    room.state = 3
                    self.SQ.delete_room(room)
                elif room.state == 2:  # 在等待队列中
                    room.state = 3
                    self.WQ.delete_room(room)
                else:#这种状态是服务已完成的状态/或者是已经关机的状态
                    room.state = 3
                # 写入数据库
                room.request_id = self.request_id
                self.request_id += 1
                room.operation = 4
                room.request_time = timezone.now()
                room.save(force_insert=True)
                Speed = ('', '高速', '中速', '低速')
                detail[room_id]['序号'].append(detailnum[room_id - 1])
                detailnum[room_id - 1] += 1
                detail[room_id]['房间号'].append(room_id)
                # detail[room_id]['请求时间'].append
                # detail[room_id]['服务开始时间'].append
                detail[room_id]['请求时间'].append(room.request_time)
                # detail[room_id]['服务时长'].append
                detail[room_id]['风速'].append(Speed[room.fan_speed])
                detail[room_id]['当前费用'].append(room.fee)
                detail[room_id]['费率'].append(room.fee_rate)
                detail[room_id]['操作类型'].append('关机')
                detail[room_id]['服务开始时间'].append(BeginTime[room_id - 1])
                BeginTime[room_id - 1] = -1

                # 关机之后的调度 开启调度函数

                if self.WQ.waiting_num != 0 and self.SQ.serving_num == 2:
                    temp = self.WQ.room_list[0]
                    self.WQ.delete_room(temp)
                    self.SQ.insert(temp)

                elif self.WQ.waiting_num != 0 and self.SQ.serving_num <= 1:
                    i = 1
                    for temp in self.WQ.room_list:
                        if i <= 2:
                            self.WQ.delete_room(temp)
                            self.SQ.insert(temp)
                        i += 1

                elif self.WQ.waiting_num != 0 and self.SQ.serving_num <= 0:
                    i = 1
                    for temp in self.WQ.room_list:
                        if i <= 3:
                            self.WQ.delete_room(temp)
                            self.SQ.insert(temp)
                        i += 1

                return room

    def cool_down_temp(self, room):
        """每分钟调整房间温度直至达到初始温度"""
        temp_difference = room.init_temp - room.current_temp
        temp_change_per_second = 0.5 / 10  # 每秒的温度变化

        # 判断是否需要升温或降温
        if abs(temp_difference) > 0.05:
            temp_change = temp_change_per_second if temp_difference > 0 else -temp_change_per_second
            room.current_temp += temp_change
            # 若温度达到或超过初始温度，则停止调整
            if (temp_difference > 0 and room.current_temp >= room.init_temp) or \
                    (temp_difference < 0 and room.current_temp <= room.init_temp):
                room.current_temp = room.init_temp
            else:
                # 继续调整温度
                timer = threading.Timer(1, self.cool_down_temp, [room])
                timer.start()

    # 达到目标温度后待机的房间启动回温算法
    def back_temp(self, room, mode):  # mode=1制热 mode=2制冷,回温算法0.5℃/min，即0.008℃/s

        """
        每分钟变化0.5度，只有目标温度到达时以及房间关机时才会启动该算法。
        算法逻辑:制热模式下，每分钟下降0.5度，也就是每秒钟下降0.008度
                如果当前温度与目标温度相差大于1度且不在SQ中，就添加到SQ中；如果SQ满了，就添加到WQ
        :param room:
        :param mode:
        :return:
        """
        if room.state == 4:#休眠状态==达到目标温度的状态
            if mode == 1:
                room.current_temp -= 0.05 #0.008333
                if abs(room.target_temp - room.current_temp) > 1:
                    if self.SQ.serving_num < 3:  # 服务队列没满
                        self.SQ.insert(room)
                    else:
                        self.WQ.insert(room)
                timer = threading.Timer(1, self.back_temp, [room, 1])  # 每1秒执行一次函数
                timer.start()
            else:
                room.current_temp += 0.05
                if abs(room.target_temp - room.current_temp) > 1 and room.current_temp > room.target_temp:
                    if self.SQ.serving_num < 3:  # 服务队列没满
                        self.SQ.insert(room)
                    else:
                        self.WQ.insert(room)
                timer = threading.Timer(1, self.back_temp, [room, 2])  # 每1秒执行一次函数
                timer.start()

    def check_target_arrive(self):
        """
        每秒遍历服务队列中的房间，将达到目标温度的房间移出服务队列，状态设为休眠
        :return:
        """
        if self.SQ.serving_num != 0:
            for room in self.SQ.room_list:
                if abs(room.current_temp - room.target_temp) < 0.1 or room.current_temp > room.target_temp:
                    room.state = 4
                    Speed = ('', '高速', '中速', '低速')
                    room_id = room.room_id
                    detail[room_id]['序号'].append(detailnum[room_id - 1])
                    detailnum[room_id - 1] += 1
                    detail[room_id]['房间号'].append(room_id)
                    # detail[room_id]['请求时间'].append
                    # detail[room_id]['服务开始时间'].append
                    detail[room_id]['请求时间'].append(timezone.now())
                    # detail[room_id]['服务时长'].append
                    detail[room_id]['风速'].append(Speed[room.fan_speed])
                    detail[room_id]['当前费用'].append(room.fee)
                    detail[room_id]['费率'].append(room.fee_rate)
                    detail[room_id]['操作类型'].append('开始休眠')
                    detail[room_id]['服务开始时间'].append(BeginTime[room_id - 1])
                    BeginTime[room_id - 1] = -1

                    self.SQ.delete_room(room)
                    if self.default_target_temp == 22:
                        self.back_temp(room, 1)
                    else:
                        self.back_temp(room, 2)
        if self.WQ.waiting_num != 0:
            for room in self.WQ.room_list:
                if abs(room.current_temp - room.target_temp) < 0.1 or room.current_temp < room.target_temp:
                    room.state = 4
                    self.WQ.delete_room(room)
                    if self.default_target_temp == 22:
                        self.back_temp(room, 1)
                    else:
                        self.back_temp(room, 2)

        timer = threading.Timer(1, self.check_target_arrive)  # 每1秒执行一次check函数
        timer.start()

    def scheduling(self):
        """
        调度算法
        服务队列：先按风速排序，风速相同的情况先入先出
        等待队列：先入先出的时间片调度
        把SQ的第一个加入WQ，WQ的第一个放入SQ末尾

        优先级调度：以高中低为三级进行优先级判断，高速风优先级最高，中速风次之，低速风优先级最低
        时间片调度：等待队列中的对象被分配2mins时长，服务队列服务时长最长的一旦到达2mins将被调度到等待队列
        :return:
        """

        #处理满员的服务队列
        if self.WQ.waiting_num != 0 and self.SQ.serving_num == 3:

            # temp = self.SQ.room_list[0]
            # self.SQ.delete_room(temp)
            # self.WQ.insert(temp)
            # temp = self.WQ.room_list[0]
            # self.WQ.delete_room(temp)
            # self.SQ.insert(temp)
            if self.SQ.room_list[0].fan_speed < self.WQ.room_list[0].fan_speed:
                # 当SQ的风扇速度大于WQ的时，什么也不做
                pass
            elif self.SQ.room_list[0].fan_speed == self.WQ.room_list[0].fan_speed:
                # 当风扇速度相等时，等待120秒后执行以下操作
                import time

                # 等待120秒，但如果在此期间服务队列元素变少，则提前退出
                start_time = time.time()
                list1=self.SQ.room_list
                flag = True
                while time.time() - start_time < 20:
                    print('正在循环')
                    list2=self.SQ.room_list
                    if list1[0]!=list2[0] or list1[1]!=list2[1] or list1[2]!=list2[2]:
                        flag = False
                        break# 提前退出等待
                    if self.SQ.room_list[0].fan_speed > self.WQ.room_list[0].fan_speed:
                        flag = False
                        break
                    print(self.SQ.room_list[0].fan_speed, self.WQ.room_list[0].fan_speed)
                    time.sleep(1)  # 1秒检查一次

                if flag ==True:
                    temp = self.SQ.room_list[0]
                    self.SQ.delete_room(temp)
                    self.WQ.insert(temp)
                    temp = self.WQ.room_list[0]
                    self.WQ.delete_room(temp)
                    self.SQ.insert(temp)
            else:
                # 当SQ的风扇速度小于WQ的时，立即执行以下操作
                print('SQ的最低风速', self.SQ.room_list[0].fan_speed)
                print('WQ的最高风速', self.WQ.room_list[0].fan_speed)
                print('出现高速，更新队列！')
                temp = self.SQ.room_list[0]
                self.SQ.delete_room(temp)
                print('风速更改后进入wq的空调：', temp.room_id)
                self.WQ.insert(temp)
                temp = self.WQ.room_list[0]
                self.WQ.delete_room(temp)
                self.SQ.insert(temp)
                print('SQ的最低风速', self.SQ.room_list[0].fan_speed)
                print('WQ的最高风速', self.WQ.room_list[0].fan_speed)

        #处理非满员的情况
        elif self.WQ.waiting_num != 0 and self.SQ.serving_num == 2:
            temp = self.WQ.room_list[0]
            self.WQ.delete_room(temp)
            self.SQ.insert(temp)

        elif self.WQ.waiting_num != 0 and self.SQ.serving_num <= 1:
            i = 1
            for temp in self.WQ.room_list:
                if i <= 2:
                    self.WQ.delete_room(temp)
                    self.SQ.insert(temp)
                i += 1

        elif self.WQ.waiting_num != 0 and self.SQ.serving_num <= 0:
            i = 1
            for temp in self.WQ.room_list:
                if i <= 3:
                    self.WQ.delete_room(temp)
                    self.SQ.insert(temp)
                i += 1
        timer = threading.Timer(2, self.scheduling)  # 每5s执行一次调度函数
        timer.start()


class Server(models.Model):
    """
    名称：服务对象
    作用：服务对象最多仅存在3个，每个服务对象对应一个房间，供调度算法以及温控使用。
    """
    STATE_CHOICE = [
        (1, 'WORKING'),
        (2, 'FREE'),
    ]

    # 服务对象的服务状态
    state = models.IntegerField(verbose_name='服务状态', choices=STATE_CHOICE, default=2)

    # 服务开始时间
    start_time = models.DateField(verbose_name="创建时间", default=timezone.now)

    # 服务对象的服务时长
    serve_time = models.FloatField(verbose_name='服务时长')

    # 服务对象所服务的房间号
    room_id = models.IntegerField(verbose_name='服务房间号')

    # 服务对象所服务房间的目标温度
    target_temp = models.IntegerField(verbose_name='目标温度')

    # 服务对象所服务房间的费用
    fee = models.FloatField(verbose_name='费用')

    # 服务对象所服务房间的费率
    fee_rate = models.FloatField(verbose_name='费率')

    # 服务对象所服务的房间的风速,默认值为2--middle
    fan_speed = models.IntegerField(verbose_name='风速', default=2)

    def set_attribute(self, room_id, start_time, current_room_temp):
        """
        服务对象的初始化，与某一个房间关联起来；
        :param room_id:
        :param start_time:
        :param current_room_temp:
        :return:
        """
        self.room_id = room_id
        self.start_time = start_time
        self.serve_time = 0.0
        self.state = 1  # 状态为working
        self.target_temp = 26
        self.fan_speed = 2  # 默认为中速风2--middle
        self.fee = 0.0
        self.fee_rate = 0.8
        return_list = [self.state, self.target_temp, self.fee_rate, self.fee]
        return return_list

    def change_target_temp(self, target_temp):
        """
        修改正在服务房间的目标温度
        :param target_temp:
        :return:
        """
        self.target_temp = target_temp
        return True

    def change_fan_speed(self, fan_speed):
        """
        修改正在服务房间的风速
        :param fan_speed:
        :return:
        """
        self.fan_speed = fan_speed
        return True

    def delete_server(self):
        """
        删除服务对象与被服务房间的关联
        :return:
        """
        #  将信息写入数据库
        # 。。。
        self.room_id = 0  # 将服务对象设置为空闲
        self.state = 2  # 状态为FREE
        return self.fee

    def set_serve_time(self):
        """
        修改服务时长
        :return:
        """
        self.serve_time = timezone.now() - self.start_time

    def set_fee(self, fee):
        """
        修改被服务房间的费用
        :return:
        """
        self.fee = fee


class Room(models.Model):
    FAN_SPEED = [
        (3, "HIGH"),
        (2, "MIDDLE"),
        (1, "LOW"),
    ]

    ROOM_STATE = [
        (1, "SERVING"),
        (2, "WAITING"),
        (3, "SHUTDOWN"),
        (4, "BACKING")  # 休眠
    ]

    OPERATION_CHOICE = [
        (1, '调温'),
        (2, '调风'),
        (3, '开机'),
        (4, '关机')
    ]

    MODE_CHOICES = [
        (1, '制热'),
        (2, '制冷')
    ]
    mode = models.IntegerField(verbose_name='工作模式', choices=MODE_CHOICES, default=1)

    # 请求号
    request_id = models.IntegerField(verbose_name="请求号", primary_key=True, default=0)

    # 请求发出时间
    request_time = models.DateTimeField(verbose_name="请求发出时间", default=django.utils.timezone.now)

    # 房间号，唯一表示房间
    room_id = models.IntegerField(verbose_name="房间号", default=0)

    # 当前温度
    current_temp = models.FloatField(verbose_name="当前温度", default=0.0)

    # 初始化温度
    init_temp = models.FloatField(verbose_name="初始化温度", default=0.0)

    # 目标温度，这里设置默认的初始温度，但是有一个问题就是管理员的init界面上，无法更改这个缺省的目标温度
    target_temp = models.FloatField(verbose_name="目标温度", default=22.0)

    # 风速，在这里已经将房间风速默认设置为了中风速
    fan_speed = models.IntegerField(verbose_name='风速', choices=FAN_SPEED, default=2)

    # 房间状态
    state = models.IntegerField(verbose_name='服务状态', choices=ROOM_STATE, default=3)

    # 费率
    fee_rate = models.FloatField(verbose_name='费率', default=0.5)

    # 费用
    fee = models.FloatField(verbose_name='费用', default=0.0)

    # 当前服务时长
    serve_time = models.IntegerField(verbose_name='当前服务时长', default=0)

    # 当前等待时长
    wait_time = models.IntegerField(verbose_name='当前等待时长', default=0)

    # 操作类型
    operation = models.IntegerField(verbose_name='操作类型', choices=OPERATION_CHOICE, default=0)

    # 调度次数
    scheduling_num = models.IntegerField(verbose_name='调度次数', default=0)


class StatisticController(models.Model):
    """
    - 名称：统计控制器
    - 作用：负责读数据库的控制器，为前台生成详单、账单
    """

    @staticmethod
    def reception_login(id, password):
        """
        感觉放在这里不是特别好，应该放在view层
        如何登录请看:https://docs.djangoproject.com/zh-hans/2.2/topics/auth/default/#how-to-log-a-user-in
        :param id:
        :param password:
        :return:
        """

    @staticmethod
    def create_rdr(room_id, begin_date, end_date):
        """
        打印详单
        :param room_id: 房间号
        :param begin_date: 起始日期
        :param end_date: endDay
        :return:    返回详单字典列表
        """
        detail = []
        rdr = Room.objects.filter(room_id=room_id, request_time__range=(begin_date, end_date)).order_by('-request_time')
        for r in rdr:
            dic = {}
            dic.update(request_id=r.request_id,
                       request_time=r.request_time,
                       room_id=r.room_id,
                       operation=r.get_operation_display(),
                       current_temp=r.current_temp,
                       target_temp=r.target_temp,
                       fan_speed=r.get_fan_speed_display(),
                       fee=r.fee)
            detail.append(dic)

        for d in detail:
            print(d)
        return detail

    @staticmethod
    def print_rdr(room_id, begin_date, end_date):
        print(detail)
        """
        打印详单
        :param room_id: 房间号
        :param begin_date: 起始日期
        :param end_date: endDay
        :return:    返回详单字典列表
        详单的表头：房间号、请求时间、服务开始时间、服务结束时间、服务时长、风速、当前费用、费率
        """
        # rdr = StatisticController.create_rdr(room_id, begin_date, end_date) 这个函数用不上了哈哈哈
        import csv
        # 文件头，一般就是数据名
        file_header = detail[int(room_id)].keys()

        # 写入数据
        with open("./result/detailed_list.csv", "w") as csvFile:
            writer = csv.writer(csvFile)
            writer.writerow(file_header)
            # 写入的内容都是以列表的形式传入函数
            for idx in range(detailnum[int(room_id) - 1] - 1):
                if detail[int(room_id)]['服务开始时间'][idx] == -1:
                    detail[int(room_id)]['服务时长'].append('-')
                else:
                    detail[int(room_id)]['服务时长'].append(
                        detail[int(room_id)]['请求时间'][idx] - detail[int(room_id)]['服务开始时间'][idx])

            for a in range(detailnum[int(room_id) - 1] - 1):
                d = []
                for b in detail[int(room_id)].values():
                    if b[a] == -1:
                        d.append('-')
                    else:
                        d.append(b[a])
                    print(d)
                writer.writerow(d)

            csvFile.close()
            return True

    @staticmethod
    def create_bill(room_id, begin_date, end_date):
        """
        创建账单
        :param room_id: 房间号
        :param begin_date: 起始日期
        :param end_date: endDay
        :return:
        """
        bill = Room.objects.filter(room_id=room_id, request_time__range=(begin_date, end_date)) \
            .order_by('-request_time')[0]
        print("fee=%f" % bill.fee)

        return bill.fee

    @staticmethod
    def print_bill(room_id, begin_date, end_date):
        """
        打印账单
        :param room_id: 房间号
        :param begin_date: 起始日期
        :param end_date: endDay
        :return:返回房间的账单费用
        账单的表头：房间号、入住时间、离开时间、空调总费用
        """
        fee = StatisticController.create_bill(room_id, begin_date, end_date)

        with open('./result/bill.csv', 'w') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["房间号", "入住时间","离开时间","空调总费用"])
            writer.writerow([room_id,begin_date,end_date,fee])
        return fee


    @staticmethod
    def create_report(room_id, type_report, year=-1, month=-1, week=-1):
        """
        创建报告
        :param room_id: 房间号
        :param type_report:报告类型,1为月报表，2为周报表
        :param month: 如果为月报，只需填入对应的月份起始日，例如“2020-5”
        :param week: 终止日期， 如果选择为周报表，则需要填入具体的起始日期“2020-x-x”以及终止日期“2020-x-x”
        :return: 将返回一个pdf报表
        """
        OPERATION_CHOICE = [
            (1, '调温'),
            (2, '调风'),
            (3, '开机'),
            (4, '关机')
        ]
        global operations
        if type_report == 1:
            """经理选择打印月报"""
            try:
                operations = Room.objects.filter(
                    Q(room_id=room_id) & (Q(request_time__year=year) & Q(request_time__month=month))).order_by(
                    '-request_time')
            except ObjectDoesNotExist:
                print("Either the room or time doesn't exist.")
        else:
            """打印周报"""
            try:
                operations = Room.objects.filter(
                    Q(room_id=room_id) & (Q(request_time__year=year) & Q(request_time__week=week))).order_by(
                    '-request_time')
            except ObjectDoesNotExist:
                print("Either the room or time doesn't exist.")
        report = {}
        report.update(room_id=room_id)
        # 开关次数
        switch_times = operations.filter(Q(operation=3) | Q(operation=4)).count()
        report.update(switch_times=switch_times)
        # 详单条数
        detailed_num = len(operations)
        report.update(detailed_num=detailed_num)
        # 调温次数
        change_temp_times = operations.filter(operation=1).count()
        report.update(change_temp_times=change_temp_times)
        # 调风次数
        change_fan_times = operations.filter(operation=2).count()
        report.update(change_fan_times=change_fan_times)

        if len(operations) == 0:
            schedule_times = 0
            request_time = 0
            fee = 0
        else:
            # 调度次数
            schedule_times = operations[0].scheduling_num
            # 请求时长
            request_time = operations[0].serve_time
            # 总费用
            fee = operations[0].fee

        report.update(schedule_times=schedule_times)
        report.update(request_time=request_time)
        report.update(fee=fee)

        print(report)
        return report

    @staticmethod
    def print_report(room_id=-1, type_report=1, year=-1, month=-1, week=-1):
        """
        创建报告
        :param room_id: 房间号，如果room_id=-1则输出所有房间的报表
        :param type_report:报告类型,1为月报表，2为周报表
        :param year:年份，不管月报、周报，都应该输入年份
        :param month: 如果为月报，只需填入对应的月份，例如“5”
        :param week: 如果选择为周报表，则需要输出第几周（相对于该年）
        :return: 将返回一个csv报表
        """
        header = [
            'room_id', 'switch_times', 'detailed_num', 'change_temp_times', 'change_fan_times',
            'schedule_times', 'request_time', 'fee'
        ]
        with open('./result/report.csv', 'w') as csv_file:
            writer = csv.DictWriter(csv_file, header)

        writer.writeheader()

        # 如果没有输入房间号，默认输出所有的房间报表
        if room_id == -1:
            for i in range(1, 6):
                report = StatisticController.create_report(room_id, type_report, year, month, week)

                writer.writerow(report)
        else:
            report = StatisticController.create_report(room_id, type_report, year, month, week)

            writer.writerow(report)

        return True

    @staticmethod
    def draw_report(room_id=-1, type_report=1, year=-1, month=-1, week=-1):
        import matplotlib.pyplot as plt
        # 如果没有输入房间号，逐个
        if room_id == -1:
            # fig, ax1 = plt.subplots(321)
            # ax1.pie(report0.values(), report0.keys())
            # plt.show()
            import numpy as np
            import pandas as pd

            # data = [[66386, 174296, 75131, 577908, 32015],
            #         [58230, 381139, 78045, 99308, 160454],
            #         [89135, 80552, 152558, 497981, 603535],
            #         [78415, 81858, 150656, 193263, 69638],
            #         [139361, 331509, 343164, 781380, 52269]]
            data = []
            global report
            rows = []
            for i in range(1,6):
                report = StatisticController.create_report(i, type_report, year, month, week)
                data.append(list(report.values())[1:-2])
                rows.append('room' + str(report['room_id']))
            columns = list(report.keys())[1:-2]
            rows = tuple(rows)
            # print(data)
            # print(columns)
            # print(rows)

            # table(cellText=None, cellColours=None,cellLoc='right', colWidths=None,rowLabels=None, rowColours=None, rowLoc='left',
            # colLabels=None, colColours=None, colLoc='center',loc='bottom', bbox=None)
            # data = [[66386, 174296, 75131, 577908, 32015],
            #         [58230, 381139, 78045, 99308, 160454],
            #         [89135, 80552, 152558, 497981, 603535],
            #         [78415, 81858, 150656, 193263, 69638],
            #         [139361, 331509, 343164, 781380, 52269]]
            # columns = ('Freeze', 'Wind', 'Flood', 'Quake', 'Hail')
            # rows = ['%d year' % x for x in (100, 50, 20, 10, 5)]
            df = pd.DataFrame(data, columns=columns,
                              index=rows)
            # print(df)
            df.plot(kind='barh', grid=True, colormap='YlGnBu', stacked=True,figsize=(15,5))  # 创建堆叠图
            print(data)
            data.reverse()
            table = plt.table(cellText=data,
                              cellLoc='center',
                              cellColours=None,
                              rowLabels=rows,
                              rowColours=plt.cm.BuPu(np.linspace(0, 0.5, len(rows)))[::-1],  # BuPu可替换成其他colormap
                              colLabels=columns,
                              colColours=plt.cm.Reds(np.linspace(0, 0.5, len(columns)))[::-1],
                              rowLoc='right',
                              loc='bottom',
                              fontsize=10.0)
            table.auto_set_font_size(False)
            table.set_fontsize(7)
            table.scale(1, 1)
            # cellText：表格文本
            # cellLoc：cell内文本对齐位置
            # rowLabels：行标签
            # colLabels：列标签
            # rowLoc：行标签对齐位置
            # loc：表格位置 → left，right，top，bottom
            plt.subplots_adjust(left=0.2, bottom=0.3)
            plt.xticks([])  # 加上的话会显得混乱，去掉就看的清了。
            plt.savefig('./result/report.png', dpi=300)
            # plt.show()
            # 不显示x轴标注
