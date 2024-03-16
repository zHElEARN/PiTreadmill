import asyncio
from bluezero import adapter
from bluezero import peripheral
from bluezero import async_tools
import struct

FTMS_SRV_UUID = '00001826-0000-1000-8000-00805f9b34fb'
TREADMILL_DATA_UUID = '00002ACD-0000-1000-8000-00805f9b34fb'

# 假设的速度、坡度和其他参数（根据实际情况调整这些值）
kmph = 8.0  # 速度（公里每小时）
incline = 5.0  # 坡度（百分比）
grade_deg = 0.0  # 坡度角度（度）
elevation_gain = 0.0  # 正面高度增益（米）

def read_treadmill_data():
    """
    生成新的跑步机速度和坡度测量值，按照蓝牙SIG规范
    """
    # 将速度和坡度转换为蓝牙SIG规范要求的单位
    inst_speed = int(kmph * 100)  # 以0.01公里/小时为单位
    inst_incline = int(incline * 10)  # 以0.1%为单位
    inst_grade = int(grade_deg * 10)  # 以0.1度为单位
    inst_elevation_gain = int(elevation_gain * 10)  # 以0.1米为单位

    # 设置标志位
    flags = 0x0018  # 对应的二进制为 '000000011000'

    # 创建一个足够大的字节数组来包含所有可能的数据字段
    treadmill_data = bytearray(34)

    # 设置标志位
    treadmill_data[0] = flags & 0xFF
    treadmill_data[1] = (flags >> 8) & 0xFF

    # 设置速度
    treadmill_data[2] = inst_speed & 0xFF
    treadmill_data[3] = (inst_speed >> 8) & 0xFF

    # 设置坡度和坡度角度
    treadmill_data[4] = inst_incline & 0xFF
    treadmill_data[5] = (inst_incline >> 8) & 0xFF
    treadmill_data[6] = inst_grade & 0xFF
    treadmill_data[7] = (inst_grade >> 8) & 0xFF

    # 设置正面高度增益
    treadmill_data[8] = inst_elevation_gain & 0xFF
    treadmill_data[9] = (inst_elevation_gain >> 8) & 0xFF

    # 返回打包后的数据
    return treadmill_data

def update_treadmill_data(characteristic):
    """更新跑步机数据特征的值，并发送通知给订阅的中央设备"""
    new_value = read_treadmill_data()
    characteristic.set_value(new_value)
    # 如果特征当前正在通知，则返回True，以继续发送通知
    return characteristic.is_notifying

def notify_callback(notifying, characteristic):
    """当中央设备订阅或取消订阅通知时调用"""
    if notifying:
        print("开始发送跑步机数据通知...")
        async_tools.add_timer_seconds(1, update_treadmill_data, characteristic)
    else:
        print("停止发送跑步机数据通知...")

def main(adapter_address):
    """创建并发布FTMS服务"""
    ftms_device = peripheral.Peripheral(adapter_address, local_name='FTMS Treadmill', appearance=0x0340)
    ftms_device.add_service(srv_id=1, uuid=FTMS_SRV_UUID, primary=True)
    ftms_device.add_characteristic(srv_id=1, chr_id=1, uuid=TREADMILL_DATA_UUID,
                                   value=read_treadmill_data(), notifying=False,
                                   flags=['read', 'notify'],
                                   read_callback=read_treadmill_data,
                                   notify_callback=notify_callback)

    ftms_device.publish()

    loop = asyncio.get_event_loop()
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("服务已停止")
        loop.stop()
    finally:
        loop.close()
        print("事件循环已关闭")

if __name__ == '__main__':
    default_adapter = list(adapter.Adapter.available())[0]
    main(default_adapter.address)
