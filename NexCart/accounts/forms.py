from django import forms
from django.contrib.auth.forms import (
    UserCreationForm,
    AuthenticationForm,
)

from .models import User, Address


class RegistrationForm(UserCreationForm):

    class Meta:

        model = User

        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'role',
            'password1',
            'password2',
        )

    def clean_email(self):

        email = self.cleaned_data.get(
            'email'
        ).lower()

        if User.objects.filter(
            email=email
        ).exists():

            raise forms.ValidationError(
                'An account with this email already exists.'
            )

        return email


class LoginForm(forms.Form):

    email = forms.CharField(
        label='Email or Username',
        widget=forms.TextInput(
            attrs={
                'placeholder':
                'Enter your email or username',
                'class':
                'form-control'
            }
        )
    )

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'placeholder':
                'Enter your password',
                'class':
                'form-control'
            }
        )
    )


class ProfileUpdateForm(forms.ModelForm):

    class Meta:

        model = User

        fields = (
            'first_name',
            'last_name',
            'phone_number',
            'profile_picture',
        )

        widgets = {
            'first_name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'First Name',
                    'id': 'id_first_name'
                }
            ),
            'last_name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Last Name',
                    'id': 'id_last_name'
                }
            ),
            'phone_number': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'e.g. +91 98765 43210',
                    'id': 'id_phone_number'
                }
            ),
            'profile_picture': forms.FileInput(
                attrs={
                    'class': 'form-control file-input-avatar',
                    'accept': 'image/*',
                    'id': 'id_profile_picture'
                }
            ),
        }


class AddressForm(forms.ModelForm):

    class Meta:
        model = Address
        fields = [
            'full_name',
            'phone',
            'address_type',
            'address_line_1',
            'address_line_2',
            'city',
            'state',
            'pincode',
            'landmark',
            'is_default',
        ]
        widgets = {
            'full_name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Full Name'
                }
            ),
            'phone': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Phone Number'
                }
            ),
            'address_type': forms.Select(
                attrs={
                    'class': 'form-control'
                }
            ),
            'address_line_1': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'House / Flat / Building'
                }
            ),
            'address_line_2': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Area / Street'
                }
            ),
            'city': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'City'
                }
            ),
            'state': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'State'
                }
            ),
            'pincode': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Pincode'
                }
            ),
            'landmark': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Landmark (Optional)'
                }
            ),
            'is_default': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input'
                }
            ),
        }