from django.db import models
from django.contrib.auth.models import User


class Portfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='portfolios')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class Holding(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='holdings')
    ticker = models.CharField(max_length=10)
    shares = models.DecimalField(max_digits=12, decimal_places=4)
    avg_cost = models.DecimalField(max_digits=12, decimal_places=2)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ticker']
        unique_together = ['portfolio', 'ticker']

    def __str__(self):
        return f"{self.ticker} x{self.shares}"


# ─── Simulation Trading Models ──────────────────────────────────────

class TradingAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trading_accounts')
    name = models.CharField(max_length=200)
    initial_capital = models.DecimalField(max_digits=14, decimal_places=2, default=100000)
    cash_balance = models.DecimalField(max_digits=14, decimal_places=2, default=100000)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class Position(models.Model):
    ASSET_TYPES = [
        ('stock', 'Stock'),
        ('option', 'Option'),
        ('future', 'Future'),
        ('forex', 'Forex'),
        ('crypto', 'Crypto'),
        ('index', 'Index ETF'),
    ]
    SIDE_CHOICES = [('long', 'Long'), ('short', 'Short')]

    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE, related_name='positions')
    ticker = models.CharField(max_length=20)
    asset_type = models.CharField(max_length=10, choices=ASSET_TYPES, default='stock')
    side = models.CharField(max_length=5, choices=SIDE_CHOICES, default='long')
    quantity = models.DecimalField(max_digits=14, decimal_places=4)
    entry_price = models.DecimalField(max_digits=14, decimal_places=4)
    is_open = models.BooleanField(default=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    realized_pnl = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    # Option-specific fields
    option_type = models.CharField(max_length=4, choices=[('call', 'Call'), ('put', 'Put')], blank=True)
    strike_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    contract_size = models.IntegerField(default=100, help_text='Multiplier (100 for options, varies for futures)')

    class Meta:
        ordering = ['-opened_at']

    def __str__(self):
        return f"{self.side.upper()} {self.quantity} {self.ticker} @ {self.entry_price}"

    @property
    def notional_value(self):
        multiplier = self.contract_size if self.asset_type in ('option', 'future') else 1
        return float(self.quantity) * float(self.entry_price) * multiplier


class Order(models.Model):
    ORDER_TYPES = [
        ('market', 'Market'),
        ('limit', 'Limit'),
        ('stop', 'Stop'),
        ('stop_limit', 'Stop Limit'),
    ]
    SIDE_CHOICES = [('buy', 'Buy'), ('sell', 'Sell')]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('filled', 'Filled'),
        ('partially_filled', 'Partially Filled'),
        ('cancelled', 'Cancelled'),
    ]
    ASSET_TYPES = Position.ASSET_TYPES

    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE, related_name='orders')
    ticker = models.CharField(max_length=20)
    asset_type = models.CharField(max_length=10, choices=ASSET_TYPES, default='stock')
    order_type = models.CharField(max_length=10, choices=ORDER_TYPES, default='market')
    side = models.CharField(max_length=4, choices=SIDE_CHOICES, default='buy')
    quantity = models.DecimalField(max_digits=14, decimal_places=4)
    limit_price = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    stop_price = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    filled_price = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='pending')
    # Option fields
    option_type = models.CharField(max_length=4, choices=[('call', 'Call'), ('put', 'Put')], blank=True)
    strike_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    filled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.side.upper()} {self.quantity} {self.ticker} ({self.status})"


class Trade(models.Model):
    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE, related_name='trades')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='trades')
    ticker = models.CharField(max_length=20)
    side = models.CharField(max_length=4)
    quantity = models.DecimalField(max_digits=14, decimal_places=4)
    price = models.DecimalField(max_digits=14, decimal_places=4)
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-executed_at']

    def __str__(self):
        return f"{self.side} {self.quantity} {self.ticker} @ {self.price}"
