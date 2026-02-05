"""
Binance DCA Bot - Main Bot Logic
=================================
บอท DCA อัตโนมัติสำหรับ Binance
รักษาเงินต้นด้วย Stop-loss และ Take-profit

วิธีใช้:
1. แก้ไข config.py ใส่ API Key
2. รัน: python bot.py
"""

import ccxt
import pandas as pd
import time
import os
from datetime import datetime, timedelta
from config import *

class DCABot:
    def __init__(self):
        """Initialize the bot"""
        self.exchange = ccxt.binance({
            'apiKey': API_KEY,
            'secret': API_SECRET,
            'sandbox': PAPER_TRADING,  # Testnet mode
            'options': {
                'defaultType': 'spot'
            }
        })
        
        # ถ้าเป็น paper trading ใช้ testnet
        if PAPER_TRADING:
            self.exchange.set_sandbox_mode(True)
            print("🧪 โหมดทดสอบ (Paper Trading) - ไม่ใช้เงินจริง")
        else:
            print("💰 โหมดใช้เงินจริง - ระวัง!")
        
        self.symbol = SYMBOL
        self.total_spent = 0
        self.total_coins = 0
        self.trades = []
        self.last_buy_time = None
        self.last_buy_price = None
        self.average_price = 0
        
        # โหลดประวัติการเทรด
        self.load_history()
    
    def load_history(self):
        """โหลดประวัติการเทรดจากไฟล์"""
        if os.path.exists(LOG_FILE):
            try:
                df = pd.read_csv(LOG_FILE)
                if not df.empty:
                    self.total_spent = df[df['type'] == 'BUY']['amount_usdt'].sum()
                    self.total_coins = df[df['type'] == 'BUY']['amount_coin'].sum() - \
                                       df[df['type'] == 'SELL']['amount_coin'].sum()
                    if self.total_coins > 0:
                        self.average_price = self.total_spent / self.total_coins
                    last_buy = df[df['type'] == 'BUY'].iloc[-1] if len(df[df['type'] == 'BUY']) > 0 else None
                    if last_buy is not None:
                        self.last_buy_price = last_buy['price']
                        self.last_buy_time = datetime.fromisoformat(last_buy['timestamp'])
                    print(f"📂 โหลดประวัติ: ใช้ไป {self.total_spent:.2f} USDT, ถือ {self.total_coins:.8f} coins")
            except Exception as e:
                print(f"⚠️ ไม่สามารถโหลดประวัติ: {e}")
    
    def save_trade(self, trade_type, price, amount_usdt, amount_coin, reason=""):
        """บันทึกการเทรด"""
        trade = {
            'timestamp': datetime.now().isoformat(),
            'type': trade_type,
            'symbol': self.symbol,
            'price': price,
            'amount_usdt': amount_usdt,
            'amount_coin': amount_coin,
            'reason': reason,
            'total_spent': self.total_spent,
            'total_coins': self.total_coins,
            'average_price': self.average_price
        }
        self.trades.append(trade)
        
        # เขียนลงไฟล์
        df = pd.DataFrame([trade])
        df.to_csv(LOG_FILE, mode='a', header=not os.path.exists(LOG_FILE), index=False)
        
        return trade
    
    def get_current_price(self):
        """ดึงราคาปัจจุบัน"""
        ticker = self.exchange.fetch_ticker(self.symbol)
        return ticker['last']
    
    def get_balance(self):
        """ดึงยอดเงินคงเหลือ"""
        balance = self.exchange.fetch_balance()
        usdt = balance['USDT']['free'] if 'USDT' in balance else 0
        coin = self.symbol.split('/')[0]
        coin_balance = balance[coin]['free'] if coin in balance else 0
        return usdt, coin_balance
    
    def buy(self, amount_usdt, reason="DCA"):
        """ซื้อเหรียญ"""
        try:
            price = self.get_current_price()
            amount_coin = amount_usdt / price
            
            if not PAPER_TRADING:
                # สั่งซื้อจริง
                order = self.exchange.create_market_buy_order(
                    self.symbol,
                    amount_coin
                )
                price = order['average'] or price
                amount_coin = order['filled']
                amount_usdt = order['cost']
            
            # อัพเดทสถิติ
            self.total_spent += amount_usdt
            self.total_coins += amount_coin
            self.average_price = self.total_spent / self.total_coins if self.total_coins > 0 else 0
            self.last_buy_price = price
            self.last_buy_time = datetime.now()
            
            # บันทึก
            trade = self.save_trade('BUY', price, amount_usdt, amount_coin, reason)
            
            print(f"✅ ซื้อ! ราคา: {price:.2f} USDT | จำนวน: {amount_coin:.8f} | เหตุผล: {reason}")
            print(f"   📊 รวมใช้ไป: {self.total_spent:.2f} USDT | ถือ: {self.total_coins:.8f} | เฉลี่ย: {self.average_price:.2f}")
            
            self.notify(f"🟢 ซื้อ {self.symbol}\nราคา: {price:.2f}\nจำนวน: {amount_coin:.8f}\nเหตุผล: {reason}")
            
            return trade
            
        except Exception as e:
            print(f"❌ ซื้อไม่สำเร็จ: {e}")
            return None
    
    def sell(self, percentage, reason=""):
        """ขายเหรียญ"""
        try:
            if self.total_coins <= 0:
                print("⚠️ ไม่มีเหรียญให้ขาย")
                return None
            
            price = self.get_current_price()
            amount_coin = self.total_coins * (percentage / 100)
            amount_usdt = amount_coin * price
            
            if not PAPER_TRADING:
                # สั่งขายจริง
                order = self.exchange.create_market_sell_order(
                    self.symbol,
                    amount_coin
                )
                price = order['average'] or price
                amount_coin = order['filled']
                amount_usdt = order['cost']
            
            # อัพเดทสถิติ
            self.total_coins -= amount_coin
            
            # บันทึก
            trade = self.save_trade('SELL', price, amount_usdt, amount_coin, reason)
            
            # คำนวณกำไร/ขาดทุน
            cost_basis = amount_coin * self.average_price
            pnl = amount_usdt - cost_basis
            pnl_percent = (pnl / cost_basis) * 100 if cost_basis > 0 else 0
            
            emoji = "🟢" if pnl >= 0 else "🔴"
            print(f"✅ ขาย! ราคา: {price:.2f} USDT | จำนวน: {amount_coin:.8f} | เหตุผล: {reason}")
            print(f"   {emoji} P/L: {pnl:.2f} USDT ({pnl_percent:.1f}%)")
            
            self.notify(f"🔴 ขาย {self.symbol}\nราคา: {price:.2f}\nจำนวน: {amount_coin:.8f}\n{emoji} P/L: {pnl:.2f} USDT ({pnl_percent:.1f}%)\nเหตุผล: {reason}")
            
            return trade
            
        except Exception as e:
            print(f"❌ ขายไม่สำเร็จ: {e}")
            return None
    
    def check_dca_time(self):
        """เช็คว่าถึงเวลา DCA หรือยัง"""
        if self.last_buy_time is None:
            return True
        
        next_buy_time = self.last_buy_time + timedelta(hours=DCA_INTERVAL_HOURS)
        return datetime.now() >= next_buy_time
    
    def check_dip_buy(self, current_price):
        """เช็คว่าราคาลงพอที่จะซื้อเพิ่มหรือไม่"""
        if self.last_buy_price is None:
            return False
        
        drop_percent = ((self.last_buy_price - current_price) / self.last_buy_price) * 100
        return drop_percent >= DIP_BUY_PERCENTAGE
    
    def check_stop_loss(self, current_price):
        """เช็ค Stop Loss"""
        if self.average_price <= 0 or self.total_coins <= 0:
            return False
        
        loss_percent = ((self.average_price - current_price) / self.average_price) * 100
        return loss_percent >= STOP_LOSS_PERCENTAGE
    
    def check_take_profit(self, current_price):
        """เช็ค Take Profit"""
        if self.average_price <= 0 or self.total_coins <= 0:
            return False
        
        profit_percent = ((current_price - self.average_price) / self.average_price) * 100
        return profit_percent >= TAKE_PROFIT_PERCENTAGE
    
    def check_budget(self):
        """เช็คว่ายังมีงบเหลือหรือไม่"""
        return self.total_spent < TOTAL_BUDGET
    
    def notify(self, message):
        """ส่งแจ้งเตือน Telegram"""
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            try:
                import requests
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'text': message})
            except:
                pass
    
    def print_status(self, current_price):
        """แสดงสถานะปัจจุบัน"""
        if self.total_coins > 0:
            current_value = self.total_coins * current_price
            pnl = current_value - self.total_spent
            pnl_percent = (pnl / self.total_spent) * 100 if self.total_spent > 0 else 0
            emoji = "🟢" if pnl >= 0 else "🔴"
            
            print(f"\n{'='*50}")
            print(f"📊 สถานะปัจจุบัน - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*50}")
            print(f"💰 ราคา {self.symbol}: {current_price:.2f} USDT")
            print(f"📈 ราคาเฉลี่ยที่ซื้อ: {self.average_price:.2f} USDT")
            print(f"🪙 จำนวนที่ถือ: {self.total_coins:.8f}")
            print(f"💵 ใช้ไปแล้ว: {self.total_spent:.2f} / {TOTAL_BUDGET} USDT")
            print(f"💎 มูลค่าปัจจุบัน: {current_value:.2f} USDT")
            print(f"{emoji} กำไร/ขาดทุน: {pnl:.2f} USDT ({pnl_percent:.1f}%)")
            print(f"{'='*50}\n")
        else:
            print(f"\n📊 ราคา {self.symbol}: {current_price:.2f} USDT | ยังไม่มีการซื้อ\n")
    
    def run(self):
        """รันบอท"""
        print(f"""
╔══════════════════════════════════════════════════╗
║           🤖 Binance DCA Bot v1.0                ║
║          รักษาเงินต้น + สร้างกำไร                  ║
╚══════════════════════════════════════════════════╝
        
⚙️ การตั้งค่า:
   • เหรียญ: {SYMBOL}
   • งบประมาณ: {TOTAL_BUDGET} USDT
   • ซื้อครั้งละ: {BUY_AMOUNT} USDT
   • DCA ทุกๆ: {DCA_INTERVAL_HOURS} ชั่วโมง
   • Stop Loss: {STOP_LOSS_PERCENTAGE}%
   • Take Profit: {TAKE_PROFIT_PERCENTAGE}%
   • Paper Trading: {'✅ เปิด' if PAPER_TRADING else '❌ ปิด (ใช้เงินจริง!)'}
        """)
        
        print("🚀 เริ่มทำงาน... กด Ctrl+C เพื่อหยุด\n")
        
        check_interval = 60  # เช็คทุก 60 วินาที
        status_interval = 300  # แสดงสถานะทุก 5 นาที
        last_status_time = 0
        
        try:
            while True:
                current_price = self.get_current_price()
                current_time = time.time()
                
                # แสดงสถานะ
                if current_time - last_status_time >= status_interval:
                    self.print_status(current_price)
                    last_status_time = current_time
                
                # 1. เช็ค Stop Loss ก่อน (สำคัญที่สุด!)
                if self.check_stop_loss(current_price):
                    print(f"🚨 STOP LOSS! ราคาลงถึง {STOP_LOSS_PERCENTAGE}%")
                    self.sell(100, f"Stop Loss at {STOP_LOSS_PERCENTAGE}%")
                    print("⏸️ หยุดบอท - รอดูสถานการณ์")
                    break
                
                # 2. เช็ค Take Profit
                if self.check_take_profit(current_price):
                    print(f"🎉 TAKE PROFIT! ราคาขึ้นถึง {TAKE_PROFIT_PERCENTAGE}%")
                    self.sell(TAKE_PROFIT_SELL_PERCENTAGE, f"Take Profit at {TAKE_PROFIT_PERCENTAGE}%")
                
                # 3. เช็คว่ายังมีงบเหลือ
                if self.check_budget():
                    
                    # 3a. เช็คว่าราคาลงมาก → ซื้อเพิ่ม
                    if self.check_dip_buy(current_price):
                        dip_amount = BUY_AMOUNT * DIP_BUY_MULTIPLIER
                        if self.total_spent + dip_amount <= TOTAL_BUDGET:
                            print(f"📉 ราคาลง {DIP_BUY_PERCENTAGE}%! ซื้อเพิ่ม")
                            self.buy(dip_amount, f"Dip Buy (-{DIP_BUY_PERCENTAGE}%)")
                    
                    # 3b. เช็คว่าถึงเวลา DCA หรือยัง
                    elif self.check_dca_time():
                        if self.total_spent + BUY_AMOUNT <= TOTAL_BUDGET:
                            self.buy(BUY_AMOUNT, "Scheduled DCA")
                        else:
                            remaining = TOTAL_BUDGET - self.total_spent
                            if remaining >= 5:  # ถ้าเหลือมากกว่า 5 USDT
                                self.buy(remaining, "Final DCA (remaining budget)")
                
                else:
                    # หมดงบแล้ว แค่รอ take profit หรือ stop loss
                    pass
                
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            print("\n\n⏹️ หยุดบอท")
            self.print_status(self.get_current_price())


if __name__ == "__main__":
    bot = DCABot()
    bot.run()
