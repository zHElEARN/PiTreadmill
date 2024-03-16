# coding=utf-8

# 导入必要的库
import asyncio
import threading
from bluezero import adapter
from bluezero import peripheral
from bluezero import async_tools
import struct
from flask import Flask, jsonify, request

# 定义蓝牙服务和特征的UUID
FTMS_SRV_UUID = '00001826-0000-1000-8000-00805f9b34fb'
TREADMILL_DATA_UUID = '00002ACD-0000-1000-8000-00805f9b34fb'

# TreadmillData 类封装了跑步机数据的功能
class TreadmillData:
    def __init__(self):
        self.kmph = 0.0
        self.incline = 0.0
        self.grade_deg = 0.0
        self.elevation_gain = 0.0

    def set_params(self, kmph, incline, grade_deg, elevation_gain):
        self.kmph = kmph
        self.incline = incline
        self.grade_deg = grade_deg
        self.elevation_gain = elevation_gain

    def get_params(self):
        return {
            'kmph': self.kmph,
            'incline': self.incline,
            'grade_deg': self.grade_deg,
            'elevation_gain': self.elevation_gain
        }

    def read_data(self):
        flags = 0x0018
        inst_speed = int(self.kmph * 100)
        inst_incline = int(self.incline * 10)
        inst_grade = int(self.grade_deg * 10)
        inst_elevation_gain = int(self.elevation_gain * 10)

        treadmill_data = bytearray(34)
        treadmill_data[0] = flags & 0xFF
        treadmill_data[1] = (flags >> 8) & 0xFF
        treadmill_data[2] = inst_speed & 0xFF
        treadmill_data[3] = (inst_speed >> 8) & 0xFF
        treadmill_data[4] = inst_incline & 0xFF
        treadmill_data[5] = (inst_incline >> 8) & 0xFF
        treadmill_data[6] = inst_grade & 0xFF
        treadmill_data[7] = (inst_grade >> 8) & 0xFF
        treadmill_data[8] = inst_elevation_gain & 0xFF
        treadmill_data[9] = (inst_elevation_gain >> 8) & 0xFF

        return treadmill_data
    
    def notify_callback(self, notifying, characteristic):
        """当中央设备订阅或取消订阅通知时调用"""
        if notifying:
            print("开始发送跑步机数据通知...")
            async_tools.add_timer_seconds(1, self.update_treadmill_data, characteristic)
        else:
            print("停止发送跑步机数据通知...")

    def update_treadmill_data(self, characteristic):
        """更新跑步机数据特征的值，并发送通知给订阅的中央设备"""
        new_value = self.read_data()
        characteristic.set_value(new_value)
        # 如果特征当前正在通知，则返回True，以继续发送通知
        return characteristic.is_notifying

# 实例化跑步机数据对象
treadmill_data = TreadmillData()

# Flask 应用
app = Flask(__name__)

@app.route('/get', methods=['GET'])
def get_treadmill():
    return jsonify(treadmill_data.get_params())

@app.route('/set', methods=['GET'])
def set_treadmill():
    kmph = request.args.get('kmph', type=float)
    incline = request.args.get('incline', type=float)
    grade_deg = request.args.get('grade_deg', type=float)
    elevation_gain = request.args.get('elevation_gain', type=float)
    
    if kmph is not None:
        treadmill_data.kmph = kmph
    if incline is not None:
        treadmill_data.incline = incline
    if grade_deg is not None:
        treadmill_data.grade_deg = grade_deg
    if elevation_gain is not None:
        treadmill_data.elevation_gain = elevation_gain
    
    return jsonify(success=True)


def run_flask_app():
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)

# 蓝牙事件循环
def run_ble():
    default_adapter = list(adapter.Adapter.available())[0]
    ftms_device = peripheral.Peripheral(default_adapter.address, local_name='Pi Treadmill', appearance=0x0540)
    ftms_device.add_service(srv_id=1, uuid=FTMS_SRV_UUID, primary=True)
    ftms_device.add_characteristic(srv_id=1, chr_id=1, uuid=TREADMILL_DATA_UUID,
                                   value=treadmill_data.read_data(), notifying=False,
                                   flags=['read', 'notify'],
                                   read_callback=treadmill_data.read_data,
                                   notify_callback=treadmill_data.notify_callback)
    ftms_device.publish()
    loop = asyncio.get_event_loop()
    loop.run_forever()

# 启动蓝牙和Flask服务器的线程
if __name__ == '__main__':
    ble_thread = threading.Thread(target=run_ble)
    ble_thread.start()
    
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()
