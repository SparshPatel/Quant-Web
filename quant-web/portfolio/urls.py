from django.urls import path
from . import views

app_name = 'portfolio'

urlpatterns = [
    path('', views.portfolio_list, name='list'),
    path('create/', views.portfolio_create, name='create'),
    path('<int:pk>/', views.portfolio_detail, name='detail'),
    path('<int:pk>/edit/', views.portfolio_edit, name='edit'),
    path('<int:pk>/delete/', views.portfolio_delete, name='delete'),
    path('<int:portfolio_pk>/holdings/add/', views.holding_add, name='holding_add'),
    path('<int:portfolio_pk>/holdings/<int:holding_pk>/delete/', views.holding_delete, name='holding_delete'),

    # Simulation Trading
    path('trading/', views.trading_account_list, name='trading_accounts'),
    path('trading/create/', views.trading_account_create, name='trading_account_create'),
    path('trading/<int:pk>/', views.trading_dashboard, name='trading_dashboard'),
    path('trading/<int:pk>/order/', views.place_order, name='place_order'),
    path('trading/<int:pk>/close/<int:position_pk>/', views.close_position_view, name='close_position'),
    path('trading/<int:pk>/cancel/<int:order_pk>/', views.cancel_order_view, name='cancel_order'),
    path('trading/<int:pk>/history/', views.trade_history, name='trade_history'),
    path('trading/<int:pk>/delete/', views.trading_account_delete, name='trading_account_delete'),

    # API endpoints for live data
    path('api/price/<str:ticker>/', views.api_live_price, name='api_live_price'),
    path('api/chart/<str:ticker>/', views.api_chart_data, name='api_chart_data'),
    path('api/positions/<int:pk>/', views.api_positions, name='api_positions'),
    path('api/equity/<int:pk>/', views.api_equity_history, name='api_equity_history'),
]
