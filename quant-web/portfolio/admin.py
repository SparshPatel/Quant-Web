from django.contrib import admin
from .models import Portfolio, Holding, TradingAccount, Position, Order, Trade


class HoldingInline(admin.TabularInline):
    model = Holding
    extra = 1


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'created_at', 'updated_at']
    inlines = [HoldingInline]


class PositionInline(admin.TabularInline):
    model = Position
    extra = 0
    readonly_fields = ['opened_at']


@admin.register(TradingAccount)
class TradingAccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'initial_capital', 'cash_balance', 'is_active', 'created_at']
    inlines = [PositionInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['ticker', 'account', 'side', 'order_type', 'quantity', 'status', 'created_at']
    list_filter = ['status', 'side', 'asset_type']


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ['ticker', 'account', 'side', 'quantity', 'price', 'executed_at']
