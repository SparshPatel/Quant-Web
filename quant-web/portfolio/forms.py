from django import forms
from .models import Portfolio, Holding, TradingAccount, Order


class PortfolioForm(forms.ModelForm):
    class Meta:
        model = Portfolio
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class HoldingForm(forms.ModelForm):
    class Meta:
        model = Holding
        fields = ['ticker', 'shares', 'avg_cost']
        widgets = {
            'ticker': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. AAPL'}),
            'shares': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'avg_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def clean_ticker(self):
        import re
        ticker = self.cleaned_data['ticker'].strip().upper()
        if not re.match(r'^[A-Z0-9.\-]{1,10}$', ticker):
            raise forms.ValidationError("Invalid ticker symbol.")
        return ticker


class TradingAccountForm(forms.ModelForm):
    class Meta:
        model = TradingAccount
        fields = ['name', 'initial_capital']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. My Paper Account'}),
            'initial_capital': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '1000'}),
        }
        labels = {
            'initial_capital': 'Starting Capital ($)',
        }


class OrderForm(forms.Form):
    ASSET_TYPES = [
        ('stock', 'Stock'),
        ('option', 'Option'),
        ('future', 'Future'),
        ('forex', 'Forex'),
        ('crypto', 'Crypto'),
        ('index', 'Index ETF'),
    ]
    ORDER_TYPES = [
        ('market', 'Market'),
        ('limit', 'Limit'),
        ('stop', 'Stop'),
    ]
    SIDE_CHOICES = [('buy', 'Buy'), ('sell', 'Sell / Short')]
    OPTION_TYPES = [('', '---'), ('call', 'Call'), ('put', 'Put')]

    ticker = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'e.g. AAPL', 'id': 'order-ticker',
            'autocomplete': 'off',
        })
    )
    asset_type = forms.ChoiceField(
        choices=ASSET_TYPES,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'order-asset-type'})
    )
    side = forms.ChoiceField(
        choices=SIDE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'order-side'})
    )
    order_type = forms.ChoiceField(
        choices=ORDER_TYPES,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'order-type'})
    )
    quantity = forms.DecimalField(
        max_digits=14, decimal_places=4, min_value=0.0001,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'step': '1', 'value': '1', 'id': 'order-qty',
        })
    )
    limit_price = forms.DecimalField(
        max_digits=14, decimal_places=4, required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'step': '0.01', 'placeholder': 'Limit price',
            'id': 'order-limit-price',
        })
    )
    stop_price = forms.DecimalField(
        max_digits=14, decimal_places=4, required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'step': '0.01', 'placeholder': 'Stop price',
            'id': 'order-stop-price',
        })
    )
    # Option fields
    option_type = forms.ChoiceField(
        choices=OPTION_TYPES, required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'order-option-type'})
    )
    strike_price = forms.DecimalField(
        max_digits=14, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'step': '0.5', 'placeholder': 'Strike',
            'id': 'order-strike',
        })
    )
    expiry_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date', 'id': 'order-expiry',
        })
    )

    def clean_ticker(self):
        import re
        ticker = self.cleaned_data['ticker'].strip().upper()
        if not re.match(r'^[A-Z0-9.\-^=]{1,20}$', ticker):
            raise forms.ValidationError("Invalid ticker symbol.")
        return ticker

    def clean(self):
        cleaned = super().clean()
        ot = cleaned.get('order_type')
        if ot == 'limit' and not cleaned.get('limit_price'):
            self.add_error('limit_price', 'Limit price required for limit orders.')
        if ot == 'stop' and not cleaned.get('stop_price'):
            self.add_error('stop_price', 'Stop price required for stop orders.')
        at = cleaned.get('asset_type')
        if at == 'option':
            if not cleaned.get('option_type'):
                self.add_error('option_type', 'Select Call or Put for options.')
            if not cleaned.get('strike_price'):
                self.add_error('strike_price', 'Strike price required for options.')
            if not cleaned.get('expiry_date'):
                self.add_error('expiry_date', 'Expiry date required for options.')
        return cleaned
