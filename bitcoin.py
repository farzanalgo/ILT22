import os
import datetime
import backtrader as bt
from backtrader_plotting import Bokeh
from backtrader_plotting.schemes import Tradimo
import pandas as pd 
import numpy as np 
import time


def backtest():
    starttime    = datetime.datetime.now()
    BASE_DIR     = os.path.dirname('/home/farzan/robot/ILT22_backtest/csv_html/')
    GammaCSV_DIR = os.path.join(BASE_DIR, "bitcoin.csv")
    plot_DIR     = os.path.join(BASE_DIR, "bitcoin.html")

    bokehPlot   = True
    matPlotLib  = False
    printlog    = True
    cash        = 10000
    commission  = 0.0004
    size        = (False  ,1)
    percent     = (True , 90)
    whole_time  = True
    from_time   = datetime.datetime.strptime('2021-01-01 00:00:00', '%Y-%m-%d %H:%M:%S')                                      
    to_time     = datetime.datetime.strptime('2022-01-31 10:00:00', '%Y-%m-%d %H:%M:%S')


    class GenericCSV_IDF22(bt.feeds.GenericCSVData):
        lines = ('f_senkou_span_a', 'f_senkou_span_b')
        params =(   ('open_time'    , 0),
                    ('open'         , 1),
                    ('high'         , 2),
                    ('low'          , 3),
                    ('close'        , 4),
                    ('volume'       ,-1),
                    ('openinterest' ,-1),
                    ('f_senkou_span_a', 5),
                    ('f_senkou_span_b', 6),
                    )



    class IDF22(bt.Strategy):
        params = (  ('h4_entry',   0.5),
                    ('h4_stop',    0.5),    
                    ('printlog',   printlog),
                    ('atr_period', 14),
                    ('profit_treshhold', 0.25),
                    ('tenkan_period'   , 13),
                    ('kijun_period'    , 34),
                    ('senkou_period'   , 55),
                    ('shift_period'    , 34),
                    ('kijun_dist'      ,  3),
                    ('kijun_trail'     ,1.2),
                    )

        def log(self, txt, dt=None, doprint=False):
            dt = dt or self.data.datetime[0]
            if self.params.printlog or doprint:
                if isinstance(dt, float):
                    dt = bt.num2date(dt)
                print('%s, %s' % (dt.isoformat(), txt))                                                   

        def __init__(self):

            #h4 candles
            # self.date       = self.datas[0].datetime
            self.open       = self.datas[0].open
            self.high       = self.datas[0].high
            self.low        = self.datas[0].low
            self.clos       = self.datas[0].close

            self.f_senkou_span_a = self.datas[0].f_senkou_span_a
            self.f_senkou_span_b = self.datas[0].f_senkou_span_b

            #dly candles
            # self.d_open     = self.datas[1].open
            # self.d_high     = self.datas[1].high
            # self.d_low      = self.datas[1].low
            # self.d_clos     = self.datas[1].close

            # self.clos[-(self.p.shift_period - 1)]   = self.clos[-(self.p.shift_period - 1)] 
            # self.d_chikou = self.d_clos[-(self.p.shift_period - 1)]

            #h4_ichi
            self.ichi                 = bt.ind.Ichimoku(
                                                        self.datas[0],
                                                        tenkan      = self.p.tenkan_period,
                                                        kijun       = self.p.kijun_period,
                                                        senkou      = self.p.senkou_period,
                                                        senkou_lead = self.p.shift_period,
                                                        chikou      = self.p.shift_period,
                                                        )
                                                        
            self.cross_clos_tenkan    = bt.ind.CrossOver(self.clos, self.ichi.tenkan_sen)
            self.cross_clos_kijun     = bt.ind.CrossOver(self.clos, self.ichi.kijun_sen)
            self.cross_clos_senkou_a  = bt.ind.CrossOver(self.clos, self.ichi.senkou_span_a)
            self.cross_clos_senkou_b  = bt.ind.CrossOver(self.clos, self.ichi.senkou_span_b)
            self.cross_tenkan_kijun   = bt.ind.CrossOver(self.ichi.tenkan_sen, self.ichi.kijun_sen)
            # self.cross_chikou_clos    = bt.ind.CrossOver(self.ichi.chikou_span ,self.clos)
            self.cross_future_kumo    = bt.ind.CrossOver(self.f_senkou_span_a, self.f_senkou_span_b)


            #daily_ichi
            # self.ichi_daily           = bt.ind.Ichimoku(
            #                                             self.datas[1],
            #                                             tenkan      = 13,
            #                                             kijun       = self.p.shift_period,
            #                                             senkou      = 55,
            #                                             senkou_lead = self.p.shift_period,
            #                                             chikou      = self.p.shift_period,
            #                                             )

            # self.cross_chikou_clos_daily    = bt.ind.CrossOver(self.ichi_daily.chikou_span ,self.clos_d)
            # self.cross_clos_kijun_daily     = bt.ind.CrossOver(self.d_clos, self.ichi_daily.kijun_sen)
            # self.cross_clos_senkou_a_daily  = bt.ind.CrossOver(self.d_clos, self.ichi_daily.senkou_span_a)
            # self.cross_clos_senkou_b_daily  = bt.ind.CrossOver(self.d_clos, self.ichi_daily.senkou_span_b)
            # self.cross_tenkan_kijun_daily   = bt.ind.CrossOver(self.ichi_daily.tenkan_sen, self.ichi_daily.kijun_sen)

            #indicators
            self.atr   = bt.ind.ATR(self.datas[0], period = self.p.atr_period)
            # self.d_atr = bt.ind.ATR(self.datas[1], period = self.p.atr_period)


            self.h4_buy_list         = []
            self.h4_buy_kijun_list   = []
            self.h4_sell_list        = []
            self.h4_sell_kijun_list  = []
            self.buy_exit_list       = []
            self.sell_exit_list      = []
            self.new_stop            = []
            self.ts_stop             = []
            self.var                 = []
            self.dist_atr            = []



        def cancel_open_orders(self):
            [self.cancel(order) for order in self.broker.orders if order.status < 4]

        def notify_order(self, order):
            side  = lambda order:   "BUY" if order.size > 0 else "SELL"
            otype = lambda order:   "  MARKET    " if order.exectype==0 else \
                                    "  CLOSE     " if order.exectype==1 else \
                                    "  LIMIT     " if order.exectype==2 else \
                                    "  STOP      " if order.exectype==3 else \
                                    "  STOP Trail" if order.exectype==5 else \
                                    "  STOPLIMIT " 

            def statement(order):
                txt=side(order)+ \
                    otype(order)+ \
                    f' {order.Status[order.status]}'\
                    f' Size: {order.executed.size}' \
                    f' Price: {order.executed.price:.2f}' \
                    f' Commission: {order.executed.comm:.2f}' 
                return txt


            if order.status is order.Completed:
                if order.exectype==0:          
                    self.broker.setcommission(0.0002)
                else: 
                    self.broker.setcommission(0.0004)

                # if order.exectype==2:           ### limit -> tp
                #     self.cancel_open_orders()
                # elif order.exectype==3:         ### stop  -> sl
                #     self.cancel_open_orders()
                # elif order.exectype==5:         ### stoptrail
                #     self.cancel_open_orders()

            if order.status not in [order.Submitted, order.Accepted]:
                txt = statement(order)
                self.log(txt)

            # if order.status in [order.Accepted]:
            #     if order.size>0:
            #         print('buy',order.ExecType, 'price:', order.price)
            #     if order.size<0:
            #         print('sell',order.ExecType, 'price:', order.price)
                # print(order)
                # txt = statement(order)
                # self.log(txt)

        def notify_trade(self, trade):
            # if trade.justopened:
            #     self.cancel_open_orders()
            # pnl_per = trade.pnl/trade.price
            # if (pnl_per) > 0.1:
            #     print(pnl_per)
            #     self.cancel_open_orders()
            #     self.close(price = self.ichi.tenkan_sen - 1*self.atr, exectype = bt.Order.Stop)

            if trade.isclosed:
                self.cancel_open_orders()

                self.h4_buy_list         = []
                self.h4_buy_kijun_list   = []
                self.h4_sell_list        = []
                self.h4_sell_kijun_list  = []
                self.new_stop            = []
                self.ts_stop             = []
                self.var                 = []
                self.dist_atr            = []

                txt = 'TRADE PNL        Gross {}, Net {}'.format(
                                        round(trade.pnl,2),
                                        round(trade.pnlcomm,2))
                self.log(txt)

        # def lot(self, stoploss, cash):



        def next(self): 

            #pnl 
            # if self.getposition(self.data).size > 0 and (abs(self.clos - self.getposition(self.data).price)/self.getposition(self.data).price) > self.p.profit_treshhold:
            #     live_pnl = (abs(self.clos - self.getposition(self.data).price)/self.getposition(self.data).price)
            #     self.var.append(1)
            # if self.getposition(self.data).size < 0 and (abs(self.clos - self.getposition(self.data).price)/self.getposition(self.data).price) > self.p.profit_treshhold:
            #     live_pnl = (abs(self.clos - self.getposition(self.data).price)/self.getposition(self.data).price)
            #     self.var.append(-1)

            # if self.getposition(self.data).size > 0 and (abs(self.clos - self.ichi.kijun_sen) > self.p.kijun_dist*self.atr):
            #     self.dist_atr.append(1)
            # if self.getposition(self.data).size < 0 and (abs(self.clos - self.ichi.kijun_sen) > self.p.kijun_dist*self.atr):
            #     self.dist_atr.append(-1)




            if (len(self.h4_buy_list) > 1) or (len(self.h4_sell_list) > 1):
                print('******************************** 2 open order simultanously *******************************************')

            #order check
            if (self.getposition(self.data).size == 0) and (len(self.h4_buy_list) == 1):
                if (self.clos > self.high[-(self.p.shift_period - 1)]) and (self.clos > self.ichi.senkou_span_a) and (self.clos > self.ichi.senkou_span_b) and (self.ichi.tenkan_sen >= self.ichi.kijun_sen) and (self.f_senkou_span_a >= self.f_senkou_span_b) and (self.clos > self.ichi.kijun_sen):
                    pass
                else:
                    self.cancel_open_orders()
                    self.h4_buy_list         = []
                    self.h4_buy_kijun_list   = []
                    self.h4_sell_list        = []
                    self.h4_sell_kijun_list  = []
                    self.new_stop            = []
                    print('H4 buy preconditions changed')

            if (self.getposition(self.data).size == 0) and (len(self.h4_sell_list) == 1):
                if (self.clos < self.low[-(self.p.shift_period - 1)]) and (self.clos < self.ichi.senkou_span_a) and (self.clos < self.ichi.senkou_span_b) and (self.ichi.tenkan_sen <= self.ichi.kijun_sen) and (self.f_senkou_span_a <= self.f_senkou_span_b) and (self.clos < self.ichi.kijun_sen):
                    pass
                else:
                    self.cancel_open_orders()
                    self.h4_buy_list         = []
                    self.h4_buy_kijun_list   = []
                    self.h4_sell_list        = []
                    self.h4_sell_kijun_list  = []
                    self.new_stop            = []
                    print('H4 sell preconditions changed')

            if (self.getposition(self.data).size > 0) and (len(self.new_stop) == 1):
                if self.clos > self.ichi.kijun_sen:
                    self.cancel_open_orders()
                    self.new_stop = []

                    print(bt.num2date(self.datas[0].datetime[0]), 'above kijun so cancel stop')

            if (self.getposition(self.data).size < 0) and (len(self.new_stop) == 1):
                if self.clos < self.ichi.kijun_sen:
                    self.cancel_open_orders()
                    self.new_stop = []

                    print(bt.num2date(self.datas[0].datetime[0]), 'below kijun so cancel stop')


            #daily trend 
            #H4 signal
            if (self.getposition(self.data).size == 0) and len(self.h4_buy_list) == 0:
                #h4 long
                if (self.clos > self.ichi.senkou_span_a) and (self.clos > self.ichi.senkou_span_b) and (self.clos > self.high[-(self.p.shift_period - 1)]) and (self.ichi.tenkan_sen >= self.ichi.kijun_sen) and (self.f_senkou_span_a >= self.f_senkou_span_b) and (self.cross_clos_kijun == +1):
                    self.cancel_open_orders()
                    buy  = self.buy(price = self.high + self.p.h4_entry*self.atr, exectype = bt.Order.Stop, transmit=False)
                    if (abs(self.clos - self.ichi.kijun_sen) < self.p.kijun_dist*self.atr):
                        stop = self.sell(price = self.low - self.p.h4_stop*self.atr, exectype = bt.Order.Stop, parent = buy, transmit=True)
                    else:
                        stop = self.sell(price = self.ichi.tenkan_sen - 1*self.atr, exectype = bt.Order.Stop, parent = buy, transmit=True)
                    self.h4_buy_list.append(buy)

                    print(bt.num2date(self.datas[0].datetime[0]), 'tf:H4 side:long signal: clos/kijun')

                elif (self.clos > self.ichi.senkou_span_a) and (self.clos > self.ichi.senkou_span_b) and (self.ichi.tenkan_sen >= self.ichi.kijun_sen) and (self.f_senkou_span_a >= self.f_senkou_span_b) and (self.clos > self.ichi.kijun_sen) and (self.clos[-1] < self.high[-self.p.shift_period]) and (self.clos > self.high[-(self.p.shift_period - 1)]):
                    self.cancel_open_orders()
                    buy  = self.buy(price = self.high + self.p.h4_entry*self.atr, exectype = bt.Order.Stop, transmit = False)
                    if (abs(self.clos - self.ichi.kijun_sen) < self.p.kijun_dist*self.atr):
                        stop = self.sell(price = self.ichi.kijun_sen - self.p.h4_stop*self.atr, exectype = bt.Order.Stop, parent = buy, transmit = True)
                    else:
                        stop = self.sell(price = self.ichi.tenkan_sen - 1*self.atr, exectype = bt.Order.Stop, parent = buy, transmit = True)
                    self.h4_buy_list.append(buy)

                    print(bt.num2date(self.datas[0].datetime[0]), 'tf:H4 side:long signal: high/chikou')

                elif (self.clos > self.ichi.senkou_span_a) and (self.clos > self.ichi.senkou_span_b) and (self.clos > self.high[-(self.p.shift_period - 1)]) and (self.f_senkou_span_a >= self.f_senkou_span_b) and (self.clos > self.ichi.kijun_sen) and (self.cross_tenkan_kijun == +1):
                    self.cancel_open_orders()
                    buy  = self.buy(price = self.high + self.p.h4_entry*self.atr, exectype = bt.Order.Stop, transmit = False)
                    if (abs(self.clos - self.ichi.kijun_sen) < self.p.kijun_dist*self.atr):
                        stop = self.sell(price = self.ichi.kijun_sen - self.p.h4_stop*self.atr, exectype = bt.Order.Stop, parent = buy, transmit = True)
                    else:
                        stop = self.sell(price = self.ichi.tenkan_sen - 1*self.atr, exectype = bt.Order.Stop, parent = buy, transmit = True)
                    self.h4_buy_list.append(buy)

                    print(bt.num2date(self.datas[0].datetime[0]), 'tf:H4 side:long signal: tenkan/kijun')

                elif  (self.clos > self.high[-(self.p.shift_period - 1)]) and (self.ichi.tenkan_sen >= self.ichi.kijun_sen) and (self.f_senkou_span_a >= self.f_senkou_span_b) and (self.clos > self.ichi.kijun_sen)  and (self.ichi.senkou_span_a > self.ichi.senkou_span_b) and (self.cross_clos_senkou_a == 1):
                    self.cancel_open_orders()
                    buy  = self.buy(price = self.high + self.p.h4_entry*self.atr, exectype = bt.Order.Stop, transmit = False)
                    if (abs(self.clos - self.ichi.kijun_sen) < self.p.kijun_dist*self.atr):
                        stop = self.sell(price = self.ichi.kijun_sen - self.p.h4_stop*self.atr, exectype = bt.Order.Stop, parent = buy, transmit = True)
                    else:
                        stop = self.sell(price = self.ichi.tenkan_sen - 1*self.atr, exectype = bt.Order.Stop, parent = buy, transmit = True)
                    self.h4_buy_list.append(buy)

                    print(bt.num2date(self.datas[0].datetime[0]), 'tf:H4 side:long signal: clos/kumo')

                elif  (self.clos > self.high[-(self.p.shift_period - 1)]) and (self.ichi.tenkan_sen >= self.ichi.kijun_sen) and (self.f_senkou_span_a >= self.f_senkou_span_b) and (self.clos > self.ichi.kijun_sen) and (self.ichi.senkou_span_a < self.ichi.senkou_span_b) and (self.cross_clos_senkou_b == 1):
                    self.cancel_open_orders()
                    buy  = self.buy(price = self.high + self.p.h4_entry*self.atr, exectype = bt.Order.Stop, transmit = False)
                    if (abs(self.clos - self.ichi.kijun_sen) < self.p.kijun_dist*self.atr):
                        stop = self.sell(price = self.ichi.kijun_sen - self.p.h4_stop*self.atr, exectype = bt.Order.Stop, parent = buy, transmit = True)
                    else:
                        stop = self.sell(price = self.ichi.tenkan_sen - 1*self.atr, exectype = bt.Order.Stop, parent = buy, transmit = True)
                    self.h4_buy_list.append(buy)

                    print(bt.num2date(self.datas[0].datetime[0]), 'tf:H4 side:long signal: clos/kumo')

                elif (self.clos > self.ichi.senkou_span_a) and (self.clos > self.ichi.senkou_span_b) and (self.clos > self.high[-(self.p.shift_period - 1)]) and (self.ichi.tenkan_sen >= self.ichi.kijun_sen) and (self.clos > self.ichi.kijun_sen) and (self.cross_future_kumo == 1):
                    self.cancel_open_orders()
                    buy  = self.buy(price = self.high + self.p.h4_entry*self.atr, exectype = bt.Order.Stop, transmit = False)
                    if (abs(self.clos - self.ichi.kijun_sen) < self.p.kijun_dist*self.atr):
                        stop = self.sell(price = self.ichi.kijun_sen - self.p.h4_stop*self.atr, exectype = bt.Order.Stop, parent = buy, transmit = True)
                    else:
                        stop = self.sell(price = self.ichi.tenkan_sen - 1*self.atr, exectype = bt.Order.Stop, parent = buy, transmit = True)
                    self.h4_buy_list.append(buy)

                    print(bt.num2date(self.datas[0].datetime[0]), 'tf:H4 side:long signal: futureSA/SB')

                # elif (self.clos > self.ichi.senkou_span_a) and (self.clos > self.ichi.senkou_span_b) and (self.clos > self.high[-(self.p.shift_period - 1)]) and (self.ichi.tenkan_sen >= self.ichi.kijun_sen) and (self.clos > self.ichi.kijun_sen) and (self.f_senkou_span_a >= self.f_senkou_span_b) and (self.cross_clos_tenkan == 1):
                #     self.cancel_open_orders()
                #     buy  = self.buy(price = self.high + self.p.h4_entry*self.atr, exectype = bt.Order.Stop, transmit = False)
                #     if (abs(self.clos - self.ichi.kijun_sen) < self.p.kijun_dist*self.atr):
                #         stop = self.sell(price = self.ichi.kijun_sen - self.p.h4_stop*self.atr, exectype = bt.Order.Stop, parent = buy, transmit = True)
                #     else:
                #         stop = self.sell(price = self.ichi.tenkan_sen - 1*self.atr, exectype = bt.Order.Stop, parent = buy, transmit = True)
                #     self.h4_buy_list.append(buy)

                #     print(bt.num2date(self.datas[0].datetime[0]), 'tf:H4 side:long signal: clos/tenkan')


            if (self.getposition(self.data).size == 0) and len(self.h4_sell_list) == 0:
                #h4 short
                if (self.clos < self.ichi.senkou_span_a) and (self.clos < self.ichi.senkou_span_b) and (self.clos < self.low[-(self.p.shift_period - 1)]) and (self.ichi.tenkan_sen <= self.ichi.kijun_sen) and (self.f_senkou_span_a <= self.f_senkou_span_b) and (self.cross_clos_kijun == -1):
                    self.cancel_open_orders()
                    sell = self.sell(price = self.low - self.p.h4_entry*self.atr, exectype = bt.Order.Stop, transmit=False)
                    if (abs(self.clos - self.ichi.kijun_sen) < self.p.kijun_dist*self.atr):
                        stop = self.buy(price = self.high + self.p.h4_stop*self.atr, exectype = bt.Order.Stop, parent = sell, transmit=True)
                    else:
                        stop = self.buy(price = self.ichi.tenkan_sen + 1*self.atr, exectype = bt.Order.Stop, parent = sell, transmit=True)
                    self.h4_sell_list.append(sell)

                    print(bt.num2date(self.datas[0].datetime[0]), 'tf:H4 side:short signal: clos/kijun')

                elif (self.clos < self.ichi.senkou_span_a) and (self.clos < self.ichi.senkou_span_b) and (self.ichi.tenkan_sen <= self.ichi.kijun_sen) and (self.f_senkou_span_a <= self.f_senkou_span_b) and (self.clos < self.ichi.kijun_sen) and (self.clos[-1] > self.low[-self.p.shift_period]) and (self.clos < self.low[-(self.p.shift_period - 1)]):
                    self.cancel_open_orders()
                    sell = self.sell(price = self.low - self.p.h4_entry*self.atr, exectype = bt.Order.Stop, transmit=False)
                    if (abs(self.clos - self.ichi.kijun_sen) < self.p.kijun_dist*self.atr):
                        stop = self.buy(price = self.ichi.kijun_sen + self.p.h4_stop*self.atr, exectype = bt.Order.Stop, parent = sell, transmit=True)
                    else:
                        stop = self.buy(price = self.ichi.tenkan_sen + 1*self.atr, exectype = bt.Order.Stop, parent = sell, transmit=True)
                    self.h4_sell_list.append(sell)

                    print(bt.num2date(self.datas[0].datetime[0]), 'tf:H4 side:short signal: low/chikou')

                elif (self.clos < self.ichi.senkou_span_a) and (self.clos < self.ichi.senkou_span_b) and (self.clos < self.low[-(self.p.shift_period - 1)]) and (self.f_senkou_span_a <= self.f_senkou_span_b) and (self.clos < self.ichi.kijun_sen) and (self.cross_tenkan_kijun == -1):
                    self.cancel_open_orders()
                    sell = self.sell(price = self.low - self.p.h4_entry*self.atr, exectype = bt.Order.Stop, transmit=False)
                    if (abs(self.clos - self.ichi.kijun_sen) < self.p.kijun_dist*self.atr):
                        stop = self.buy(price = self.ichi.kijun_sen + self.p.h4_stop*self.atr, exectype = bt.Order.Stop, parent = sell, transmit=True)
                    else:
                        stop = self.buy(price = self.ichi.tenkan_sen + 1*self.atr, exectype = bt.Order.Stop, parent = sell, transmit=True)
                    self.h4_sell_list.append(sell)

                    print(bt.num2date(self.datas[0].datetime[0]), 'tf:H4 side:short signal: tenkan/kijun')

                elif  (self.clos < self.low[-(self.p.shift_period - 1)]) and (self.ichi.tenkan_sen <= self.ichi.kijun_sen) and (self.f_senkou_span_a <= self.f_senkou_span_b) and (self.clos < self.ichi.kijun_sen) and (self.ichi.senkou_span_a < self.ichi.senkou_span_b) and (self.cross_clos_senkou_a == -1):
                    self.cancel_open_orders()
                    sell = self.sell(price = self.low - self.p.h4_entry*self.atr, exectype = bt.Order.Stop, transmit=False)
                    if (abs(self.clos - self.ichi.kijun_sen) < self.p.kijun_dist*self.atr):
                        stop = self.buy(price = self.ichi.kijun_sen + self.p.h4_stop*self.atr, exectype = bt.Order.Stop, parent = sell, transmit=True)
                    else:
                        stop = self.buy(price = self.ichi.tenkan_sen + 1*self.atr, exectype = bt.Order.Stop, parent = sell, transmit=True)
                    self.h4_sell_list.append(sell)

                    print(bt.num2date(self.datas[0].datetime[0]), 'tf:H4 side:short signal: clos/kumo')

                elif  (self.clos < self.low[-(self.p.shift_period - 1)]) and (self.ichi.tenkan_sen <= self.ichi.kijun_sen) and (self.f_senkou_span_a <= self.f_senkou_span_b) and (self.clos < self.ichi.kijun_sen) and (self.ichi.senkou_span_a > self.ichi.senkou_span_b) and (self.cross_clos_senkou_b == -1):
                    self.cancel_open_orders()
                    sell = self.sell(price = self.low - self.p.h4_entry*self.atr, exectype = bt.Order.Stop, transmit=False)
                    if (abs(self.clos - self.ichi.kijun_sen) < self.p.kijun_dist*self.atr):
                        stop = self.buy(price = self.ichi.kijun_sen + self.p.h4_stop*self.atr, exectype = bt.Order.Stop, parent = sell, transmit=True)
                    else:
                        stop = self.buy(price = self.ichi.tenkan_sen + 1*self.atr, exectype = bt.Order.Stop, parent = sell, transmit=True)
                    self.h4_sell_list.append(sell)

                    print(bt.num2date(self.datas[0].datetime[0]), 'tf:H4 side:short signal: clos/kumo')

                elif (self.clos < self.ichi.senkou_span_a) and (self.clos < self.ichi.senkou_span_b) and (self.clos < self.low[-(self.p.shift_period - 1)]) and (self.ichi.tenkan_sen <= self.ichi.kijun_sen) and (self.clos < self.ichi.kijun_sen) and (self.cross_future_kumo == -1):
                    self.cancel_open_orders()
                    sell = self.sell(price = self.low - self.p.h4_entry*self.atr, exectype = bt.Order.Stop, transmit=False)
                    if (abs(self.clos - self.ichi.kijun_sen) < self.p.kijun_dist*self.atr):
                        stop = self.buy(price = self.ichi.kijun_sen + self.p.h4_stop*self.atr, exectype = bt.Order.Stop, parent = sell, transmit=True)
                    else:
                        stop = self.buy(price = self.ichi.tenkan_sen + 1*self.atr, exectype = bt.Order.Stop, parent = sell, transmit=True)
                    self.h4_sell_list.append(sell)

                    print(bt.num2date(self.datas[0].datetime[0]), 'tf:H4 side:short signal: futureSA/SB')

                # elif (self.clos < self.ichi.senkou_span_a) and (self.clos < self.ichi.senkou_span_b) and (self.clos < self.high[-(self.p.shift_period - 1)]) and (self.ichi.tenkan_sen <= self.ichi.kijun_sen) and (self.clos < self.ichi.kijun_sen) and (self.f_senkou_span_a <= self.f_senkou_span_b) and (self.cross_clos_tenkan == -1):
                #     self.cancel_open_orders()
                #     sell = self.sell(price = self.low - self.p.h4_entry*self.atr, exectype = bt.Order.Stop, transmit=False)
                #     if (abs(self.clos - self.ichi.kijun_sen) < self.p.kijun_dist*self.atr):
                #         stop = self.buy(price = self.ichi.kijun_sen + self.p.h4_stop*self.atr, exectype = bt.Order.Stop, parent = sell, transmit=True)
                #     else:
                #         stop = self.buy(price = self.ichi.tenkan_sen + 1*self.atr, exectype = bt.Order.Stop, parent = sell, transmit=True)
                #     self.h4_sell_list.append(sell)

                #     print(bt.num2date(self.datas[0].datetime[0]), 'tf:H4 side:short signal: clos/tenkan')

            #exit
            #TRAILING STOPLOSS BELOW kijun_sen
            if (self.getposition(self.data).size > 0) and (self.low < (self.ichi.kijun_sen - self.p.kijun_trail*self.atr)) and (len(self.var) == 0 and len(self.dist_atr) == 0):
                self.close()
                self.cancel_open_orders()

                print(bt.num2date(self.datas[0].datetime[0]), 'close by trailing kijun')

            elif (self.getposition(self.data).size < 0) and (self.high > (self.ichi.kijun_sen + self.p.kijun_trail*self.atr)) and (len(self.var) == 0 and len(self.dist_atr) == 0):
                self.close()
                self.cancel_open_orders()

                print(bt.num2date(self.datas[0].datetime[0]), 'close by trailing kijun')

            elif (self.getposition(self.data).size > 0) and (self.cross_clos_kijun == -1) and (len(self.var) == 0 and len(self.dist_atr) == 0 and (len(self.new_stop) == 0)):
                self.cancel_open_orders()
                new_stoploss = self.close(price = self.low - 0.5*self.atr, exectype = bt.Order.Stop)
                self.new_stop.append(new_stoploss)

                print(bt.num2date(self.datas[0].datetime[0]), 'close by kijun')

            elif (self.getposition(self.data).size < 0) and (self.cross_clos_kijun == +1) and (len(self.var) == 0 and len(self.dist_atr) == 0 and (len(self.new_stop) == 0)):
                self.cancel_open_orders()
                new_stoploss = self.close(price = self.high + 0.5*self.atr, exectype = bt.Order.Stop)
                self.new_stop.append(new_stoploss)

                print(bt.num2date(self.datas[0].datetime[0]), 'close by kijun')


            # elif (self.getposition(self.data).size > 0) and (len(self.var) != 0 or len(self.dist_atr) != 0) and self.clos < self.ichi.tenkan_sen - self.atr:
            #     self.cancel_open_orders()
            #     ts_stop = self.close()
            #     # self.ts_stop.append(ts_stop)

            #     print(bt.num2date(self.datas[0].datetime[0]), 'more than 0.25 or 3atr so stop by tenkan sen')

            # elif (self.getposition(self.data).size < 0) and (len(self.var) != 0 or len(self.dist_atr) != 0) and self.clos > self.ichi.tenkan_sen + self.atr:
            #     self.cancel_open_orders()
            #     ts_stop = self.close()
            #     # self.ts_stop.append(ts_stop)

            #     print(bt.num2date(self.datas[0].datetime[0]), 'more than 0.25 or 3atr so stop by tenkan sen')



        def stop(self):
            global fvalue                                                                                 
            txt =   f'Initial cash:{self.broker.startingcash} '\
                    f'Final cash:{self.broker.getvalue()}'
            print(txt)
            fvalue = self.broker.getvalue()



    cerebro = bt.Cerebro(cheat_on_open = True)  #cheat_on_open = True
    cerebro.broker.setcash(cash)                                                                        
    # cerebro.broker.setcommission(commission)
    cerebro.broker.setcommission(commission = commission)                                                 

    if whole_time:
        data = GenericCSV_IDF22(
                                dataname  = GammaCSV_DIR, 
                                dtformat  = 2,
                                timeframe = bt.TimeFrame.Days,
                                compression = 1,
                                )
    else:
        data = GenericCSV_IDF22(dataname=GammaCSV_DIR, 
                            dtformat = 2,
                            fromdate = from_time,
                            todate   = to_time, 
                            timeframe = bt.TimeFrame.Days,
                            compression = 1)

    codename = '510300'
    cerebro.adddata(data, name=codename)
    # cerebro.addcalendar(MyCalendar)
    # cerebro.resampledata(data, timeframe=bt.TimeFrame.Weeks, compression=1, name=codename)


    cerebro.addstrategy(IDF22)

    if size[0]:
        cerebro.addsizer(bt.sizers.FixedSize,   stake    = size[1])  
    elif percent[0]: 
        cerebro.addsizer(bt.sizers.PercentSizer,percents = percent[1])  

    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, 
                        timeframe       = bt.TimeFrame.Days, 
                        compression     = 1, 
                        riskfreerate    = 0.05,
                        #convertrate     = False, 
                        annualize       = True, 
                        factor          = 365)                   
    cerebro.addanalyzer(bt.analyzers.DrawDown) 

    cerebro.run()

    endtime = datetime.datetime.now()
    print('Process time duration:',endtime-starttime)

    if matPlotLib:
        cerebro.plot(style              = 'candlestick',
                    barup               = 'green',
                    volume              = False)
    if bokehPlot:
        b = Bokeh(  style               = 'bar', 
                    plot_mode           = 'single', 
                    scheme              = Tradimo(), 
                    legend_text_color   = '#000000', 
                    filename            = plot_DIR,
                    volume              = False)
        cerebro.plot(b)

    return fvalue



backtest()