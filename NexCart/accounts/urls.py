from django.urls import path, reverse_lazy
from django.contrib.auth import (
    views as auth_views,
)

from .views import (
    address_list,
    add_address,
    admin_dashboard,
    delete_address,
    edit_address,
    login_view,
    logout_view,
    profile_view,
    register_view,
    set_default_address,
    verify_email,
)




urlpatterns = [

    path(
        'register/',
        register_view,
        name='register'
    ),

    path(
        'login/',
        login_view,
        name='login'
    ),

    path(
        'logout/',
        logout_view,
        name='logout'
    ),

    path(
        'profile/',
        profile_view,
        name='profile'
    ),

    path(
        'verify-email/<uidb64>/<token>/',
        verify_email,
        name='verify_email'
    ),

    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='accounts/password_reset.html',
            success_url=reverse_lazy('password_reset_done')
        ),
        name='password_reset'
    ),

    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html'
        ),
        name='password_reset_done'
    ),

    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            success_url=reverse_lazy('password_reset_complete')
        ),
        name='password_reset_confirm'
    ),

    path(
        'password-reset-complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),

    path(
        'change-password/',
        auth_views.PasswordChangeView.as_view(
            template_name='accounts/change_password.html',
            success_url=reverse_lazy('profile')
        ),
        name='change_password'
    ),

    path(
        'addresses/',
        address_list,
        name='address_list'
    ),

    path(
        'addresses/add/',
        add_address,
        name='add_address'
    ),

    path(
        'addresses/<int:address_id>/edit/',
        edit_address,
        name='edit_address'
    ),

    path(
        'addresses/<int:address_id>/delete/',
        delete_address,
        name='delete_address'
    ),

    path(
        'addresses/<int:address_id>/default/',
        set_default_address,
        name='set_default_address'
    ),

    # Admin Dashboard
    path(
        'dashboard/',
        admin_dashboard,
        name='admin_dashboard'
    ),
]


