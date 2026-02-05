# 🤖 Binance DCA Bot

บอท DCA อัตโนมัติสำหรับ Binance - **รักษาเงินต้น + สร้างกำไร**

## ✨ ฟีเจอร์

- ✅ **DCA อัตโนมัติ** - ซื้อสม่ำเสมอตามเวลาที่กำหนด
- ✅ **Dip Buying** - ซื้อเพิ่มเมื่อราคาลง
- ✅ **Stop Loss** - ขายอัตโนมัติเมื่อขาดทุนถึงจุดที่ตั้ง
- ✅ **Take Profit** - ขายทำกำไรเมื่อราคาขึ้น
- ✅ **Paper Trading** - ทดสอบโดยไม่ใช้เงินจริง
- ✅ **บันทึกประวัติ** - เก็บ log ทุกการเทรด
- ✅ **แจ้งเตือน Telegram** (optional)

## 📋 ความต้องการ

- Python 3.8+
- บัญชี Binance + API Key

## 🚀 วิธีติดตั้ง

```bash
# 1. Clone repo
git clone https://github.com/saridpong/crypto-bot.git
cd crypto-bot

# 2. ติดตั้ง dependencies
pip install -r requirements.txt

# 3. แก้ไข config.py
nano config.py
```

## ⚙️ การตั้งค่า (config.py)

```python
# API Keys (จาก Binance)
API_KEY = "your_api_key"
API_SECRET = "your_api_secret"

# เหรียญที่จะเทรด
SYMBOL = "BTC/USDT"

# งบประมาณ (USDT)
TOTAL_BUDGET = 300  # ~10,000 บาท

# ซื้อครั้งละ
BUY_AMOUNT = 10  # USDT

# ซื้อทุกๆ กี่ชั่วโมง
DCA_INTERVAL_HOURS = 24

# Stop Loss / Take Profit
STOP_LOSS_PERCENTAGE = 15
TAKE_PROFIT_PERCENTAGE = 30

# โหมดทดสอบ
PAPER_TRADING = True  # เปลี่ยนเป็น False เมื่อพร้อม
```

## ▶️ วิธีรัน

```bash
# รันบอท
python bot.py

# รันใน background
nohup python bot.py > bot.log 2>&1 &
```

## 📊 กลยุทธ์

```
┌─────────────────────────────────────────────────┐
│                  DCA Strategy                   │
├─────────────────────────────────────────────────┤
│  📅 ซื้อทุกวัน (หรือตามที่ตั้ง)                    │
│  📉 ราคาลง 5%? → ซื้อเพิ่ม 2 เท่า                 │
│  🛡️ ขาดทุน 15%? → Stop Loss (ขายหมด)           │
│  🎯 กำไร 30%? → Take Profit (ขาย 50%)          │
└─────────────────────────────────────────────────┘
```

## ⚠️ คำเตือน

- **ใช้เงินที่เสียได้เท่านั้น**
- **เริ่มจาก Paper Trading ก่อนเสมอ**
- **ไม่รับประกันกำไร** - การลงทุนมีความเสี่ยง
- **เก็บ API Key ให้ดี** - อย่าเปิด Withdrawal permission

## 📝 License

MIT License - ใช้ได้ตามสบาย แต่ความเสี่ยงเป็นของคุณเอง!
