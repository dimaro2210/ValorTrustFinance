from django.shortcuts import render
from datetime import datetime

# Create your views here.

from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import render, redirect
from .forms import CustomUserCreationForm  # Ensure you have your custom form imported
from .decorators import unauthenticated_user  # Import your decorator
from django.contrib.auth.decorators import login_required
from .decorators import *
from .forms import *
from .models import *
from .utilis import *

@login_required(login_url='loginview')
def account_frozen_page(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # Handle the case where the profile doesn't exist
        user_profile = UserProfile.objects.create(user=request.user)
    context = {
        'user_profile': user_profile,
    }
    return render(request, 'bank_app/account_frozen_page.html', context)


@unauthenticated_user
def register(request):
    form = UserCreationForm()

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            return redirect('loginview')

    context = {'form': form}
    return render(request, 'bank_app/register.html', context)

@unauthenticated_user
def loginview(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('reset_profile')
        else:
            messages.info(request, 'Username OR password is incorrect')
    context = {}
    return render(request, 'bank_app/login.html')
    
def home(request):
    return render(request, 'bank_app/index.html')

@login_required
def dashboard(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # Handle the case where the profile doesn't exist
        user_profile = UserProfile.objects.create(user=request.user)

    # Fetch the last 10 transactions
    transactions = Transaction.objects.filter(user=user_profile.user).order_by('-timestamp')[:10]
    balance = user_profile.balance
    currency = user_profile.currency
    account_type = user_profile.account_type
    context = {'currency':currency, 'balance':balance, 'user_profile':user_profile, 'transactions':transactions, 'account_type':account_type}
    return render(request, 'bank_app/dashboard.html', context)

def verify(request):
    return render(request, 'bank_app/verify.html')

@login_required
def setting(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # Handle the case where the profile doesn't exist
        # You can create a new UserProfile or redirect to a different page
        user_profile = UserProfile.objects.create(user=request.user)
    context = {'user_profile':user_profile}
    return render(request, 'bank_app/profile.html', context)

@login_required
def transactionPage(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # Handle the case where the profile doesn't exist
        user_profile = UserProfile.objects.create(user=request.user)

    # Fetch the last 10 transactions
    currency = user_profile.currency
    balance = user_profile.balance
    transactions = Transaction.objects.filter(user=user_profile.user).order_by('-timestamp')[:10]
    context = {'currency':currency, 'balance':balance, 'user_profile':user_profile, 'transactions':transactions}
    return render(request, 'bank_app/transactionPage.html', context)

@login_required
def Upgrade_Account(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(user=request.user)

    # Account upgrade status message
    if user_profile.is_upgraded:
        message = 'Account upgraded successfully'
    else:
        message = 'Account upgrade processing. Contact support for more information.'

    # Months and years for dropdowns (this might still be useful for displaying in the form)
    months = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
    current_year = datetime.now().year
    years = [str(year) for year in range(current_year, current_year + 10)]

    # If the form is submitted via POST
    if request.method == "POST":
        # Get form data (Card Number, CVV, Expiry Date)
        card_number = request.POST.get('card_number')
        cvv = request.POST.get('cvv')
        expiry_date = request.POST.get('expiry_date')  # This is now the full MM/YYYY value

        # Validate card number, CVV, and expiry date
        if user_profile.card_number != card_number:
            messages.error(request, 'Invalid card number. Please check and try again.')
            return redirect('Upgrade_Account')  # Redirect to the same page with error message

        if user_profile.cvv != cvv:
            messages.error(request, 'Invalid CVV. Please check and try again.')
            return redirect('Upgrade_Account')  # Redirect to the same page with error message

        # Compare the expiry date with the one stored in the profile (no need for separate month/year comparison)
        if user_profile.expiry_date != expiry_date:
            messages.error(request, 'Invalid expiration date. Please check and try again.')
            return redirect('Upgrade_Account')  # Redirect to the same page with error message

        # If card details are correct, update the is_upgraded flag
        user_profile.is_upgraded = True  # Mark the account as upgraded
        user_profile.save()  # Save the changes to the database

        # Add a success message to be displayed on the next page
        messages.success(request, 'Account upgraded successfully!')

        # Redirect to the 'dashboard' view after form submission
        return redirect('pendingPro')  # Redirect to the dashboard view

    # Context to render on the page
    context = {
        'user_profile': user_profile,
        'message': message,
        'months': months,
        'years': years,
    }
    return render(request, 'bank_app/account_upgrade.html', context)

@check_frozen
@login_required
def bank(request): 
    user_profile = request.user.userprofile  # Retrieve user profile associated with the current user

    if request.method == 'POST':
        form = DepositForm(request.POST, user_profile=user_profile)
        if form.is_valid():
            try:
                if not user_profile.is_linked:
                    form.add_error(None, "Please activate your account before making a deposit.")
                else:
                    deposit_amount = form.cleaned_data['amount']
                    if deposit_amount <= 0:
                        form.add_error('amount', "Deposit amount must be greater than zero.")
                    else:
                        # Create a transaction record without deducting the balance
                        Transaction.objects.create(
                            user=user_profile.user,
                            amount=deposit_amount,
                            balance_after=user_profile.balance,  # Balance remains unchanged
                            description='Pending'
                        )

                        return redirect('imf')  # Redirect to dashboard view after processing the deposit
            except ValidationError as e:
                form.add_error(None, str(e))
    else:
        form = DepositForm(user_profile=user_profile)

    context = {
        'user_profile': user_profile,
        'form': form,
    }
    return render(request, 'bank_app/bank.html', context)

@check_frozen
@login_required
def crypto(request):
    user_profile = request.user.userprofile  # Retrieve user profile associated with the current user

    if request.method == 'POST':
        form = DepositForm(request.POST, user_profile=user_profile)
        if form.is_valid():
            try:
                if not user_profile.is_linked:
                    form.add_error(None, "Please activate your account before making a deposit.")
                else:
                    deposit_amount = form.cleaned_data['amount']
                    if deposit_amount <= 0:
                        form.add_error('amount', "Deposit amount must be greater than zero.")
                    else:
                        # Create a transaction record without deducting the balance
                        Transaction.objects.create(
                            user=user_profile.user,
                            amount=deposit_amount,
                            balance_after=user_profile.balance,  # Balance remains unchanged
                            description='Pending'
                        )

                        return redirect('imf')  # Redirect to dashboard view after processing the deposit
            except ValidationError as e:
                form.add_error(None, str(e))
    else:
        form = DepositForm(user_profile=user_profile)

    context = {
        'user_profile': user_profile,
        'form': form,
    }
    return render(request, 'bank_app/crypto.html', context)

@check_frozen
@login_required
def paypal(request):
    user_profile = request.user.userprofile  # Retrieve user profile associated with the current user

    if request.method == 'POST':
        form = DepositForm(request.POST, user_profile=user_profile)
        if form.is_valid():
            try:
                if not user_profile.is_linked:
                    form.add_error(None, "Please activate your account before making a deposit.")
                else:
                    deposit_amount = form.cleaned_data['amount']
                    if deposit_amount <= 0:
                        form.add_error('amount', "Deposit amount must be greater than zero.")
                    else:
                        # Create a transaction record without deducting the balance
                        Transaction.objects.create(
                            user=user_profile.user,
                            amount=deposit_amount,
                            balance_after=user_profile.balance,  # Balance remains unchanged
                            description='Pending'
                        )

                        return redirect('imf')  # Redirect to dashboard view after processing the deposit
            except ValidationError as e:
                form.add_error(None, str(e))
    else:
        form = DepositForm(user_profile=user_profile)

    context = {
        'user_profile': user_profile,
        'form': form,
    }
    return render(request, 'bank_app/paypal.html', context)

@login_required
def linking_view(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # Handle the case where the profile doesn't exist
        user_profile = UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
        form = LinkingCodeForm(request.POST)
        if form.is_valid():
            # Check if the linking code matches
            entered_code = form.cleaned_data['linking_code']
            if entered_code == user_profile.linking_code:
                messages.success(request, 'Account successfully Activated.')
                # Handle linking logic here, e.g., set a flag in UserProfile
                user_profile.is_linked = True
                user_profile.save()
                return redirect('dashboard')  # Redirect to dashboard or another view
            else:
                messages.error(request, 'Invalid activation code. Please try again.')
        else:
            messages.error(request, 'Form validation failed. Please check the input.')

    else:
        form = LinkingCodeForm()

    context = {
        'form': form,
        'user_profile': user_profile,
    }
    return render(request, 'bank_app/linking_view.html', context)

@check_frozen
@login_required
def skrill(request):
    user_profile = request.user.userprofile  # Retrieve user profile associated with the current user

    if request.method == 'POST':
        form = DepositForm(request.POST, user_profile=user_profile)
        if form.is_valid():
            try:
                if not user_profile.is_linked:
                    form.add_error(None, "Please activate your account before making a deposit.")
                else:
                    deposit_amount = form.cleaned_data['amount']
                    if deposit_amount <= 0:
                        form.add_error('amount', "Deposit amount must be greater than zero.")
                    else:
                        # Create a transaction record without deducting the balance
                        Transaction.objects.create(
                            user=user_profile.user,
                            amount=deposit_amount,
                            balance_after=user_profile.balance,  # Balance remains unchanged
                            description='Pending'
                        )

                        return redirect('otp')  # Redirect to dashboard view after processing the deposit
            except ValidationError as e:
                form.add_error(None, str(e))
    else:
        form = DepositForm(user_profile=user_profile)

    context = {
        'user_profile': user_profile,
        'form': form,
    }
    return render(request, 'bank_app/skrill.html', context)

@check_frozen
@login_required
def G_cash(request):
    user_profile = request.user.userprofile  # Retrieve user profile associated with the current user

    if request.method == 'POST':
        form = DepositForm(request.POST, user_profile=user_profile)
        if form.is_valid():
            try:
                if not user_profile.is_linked:
                    form.add_error(None, "Please activate your account before making a deposit.")
                else:
                    deposit_amount = form.cleaned_data['amount']
                    if deposit_amount <= 0:
                        form.add_error('amount', "Deposit amount must be greater than zero.")
                    else:
                        # Create a transaction record without deducting the balance
                        Transaction.objects.create(
                            user=user_profile.user,
                            amount=deposit_amount,
                            balance_after=user_profile.balance,  # Balance remains unchanged
                            description='Pending'
                        )

                        return redirect('otp')  # Redirect to dashboard view after processing the deposit
            except ValidationError as e:
                form.add_error(None, str(e))
    else:
        form = DepositForm(user_profile=user_profile)

    context = {
        'user_profile': user_profile,
        'form': form,
    }
    return render(request, 'bank_app/G_cash.html', context)

@check_frozen
@login_required
def trust_wise(request):
    user_profile = request.user.userprofile  # Retrieve user profile associated with the current user

    if request.method == 'POST':
        form = DepositForm(request.POST, user_profile=user_profile)
        if form.is_valid():
            try:
                if not user_profile.is_linked:
                    form.add_error(None, "Please activate your account before making a deposit.")
                else:
                    deposit_amount = form.cleaned_data['amount']
                    if deposit_amount <= 0:
                        form.add_error('amount', "Deposit amount must be greater than zero.")
                    else:
                        # Create a transaction record without deducting the balance
                        Transaction.objects.create(
                            user=user_profile.user,
                            amount=deposit_amount,
                            balance_after=user_profile.balance,  # Balance remains unchanged
                            description='Pending'
                        )

                        return redirect('otp')  # Redirect to dashboard view after processing the deposit
            except ValidationError as e:
                form.add_error(None, str(e))
    else:
        form = DepositForm(user_profile=user_profile)

    context = {
        'user_profile': user_profile,
        'form': form,
    }
    return render(request, 'bank_app/wise.html', context)

@check_frozen
@login_required
def western_union(request): 
    user_profile = request.user.userprofile  # Retrieve user profile associated with the current user

    if request.method == 'POST':
        form = DepositForm(request.POST, user_profile=user_profile)
        if form.is_valid():
            try:
                if not user_profile.is_linked:
                    form.add_error(None, "Please activate your account before making a deposit.")
                else:
                    deposit_amount = form.cleaned_data['amount']
                    if deposit_amount <= 0:
                        form.add_error('amount', "Deposit amount must be greater than zero.")
                    else:
                        # Remove balance deduction logic
                        # Create a transaction record
                        Transaction.objects.create(
                            user=user_profile.user,
                            amount=deposit_amount,
                            balance_after=user_profile.balance,  # Keep the balance as is
                            description='Pending'  # Change description if needed (e.g., Deposit instead of )
                        )

                        return redirect('otp')  # Redirect to dashboard view after processing the deposit
            except ValidationError as e:
                form.add_error(None, str(e))
    else:
        form = DepositForm(user_profile=user_profile)

    context = {
        'user_profile': user_profile,
        'form': form,
    }
    return render(request, 'bank_app/western_union.html', context)

@check_frozen
@login_required
def payoneer(request):
    user_profile = request.user.userprofile  # Retrieve user profile associated with the current user

    if request.method == 'POST':
        form = DepositForm(request.POST, user_profile=user_profile)
        if form.is_valid():
            try:
                if not user_profile.is_linked:
                    form.add_error(None, "Please activate your account before making a deposit.")
                else:
                    deposit_amount = form.cleaned_data['amount']
                    if deposit_amount <= 0:
                        form.add_error('amount', "Deposit amount must be greater than zero.")
                    else:
                        # Remove balance deduction logic
                        # Create a transaction record
                        Transaction.objects.create(
                            user=user_profile.user,
                            amount=deposit_amount,
                            balance_after=user_profile.balance,  # Keep the balance as is
                            description='Pending'  # Change description if needed (e.g., Deposit instead of Debit)
                        )

                        return redirect('otp')  # Redirect to dashboard view after processing the deposit
            except ValidationError as e:
                form.add_error(None, str(e))
    else:
        form = DepositForm(user_profile=user_profile)

    context = {
        'user_profile': user_profile,
        'form': form,
    }
    return render(request, 'bank_app/payoneer.html', context)

@login_required
def otp(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # Handle the case where the profile doesn't exist
        user_profile = UserProfile.objects.create(user=request.user)

    # Check if the user is authenticated and try to get the user's profile
    if request.user.is_authenticated:
        try:
            userprofile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            # Handle the case where the UserProfile does not exist
            userprofile = None

    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            otp_code_input = form.cleaned_data['otp']
            # Validate the OTP here (e.g., check if it matches the expected value)
            if validate_otp(otp_code_input, user_profile):  # Define this function based on your validation logic
                # Redirect to success page or dashboard
                return redirect('imf')
            else:
                form.add_error(None, 'Invalid OTP code')
    else:
        form = OTPForm()

    context = {
        'user_profile': user_profile,
        'userprofile': userprofile,
        'form': form
    }
    return render(request, 'bank_app/otp.html', context)

@login_required
def aml(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # Handle the case where the profile doesn't exist
        user_profile = UserProfile.objects.create(user=request.user)

    # Check if the user is authenticated and try to get the user's profile
    if request.user.is_authenticated:
        try:
            userprofile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            # Handle the case where the UserProfile does not exist
            userprofile = None

    if request.method == 'POST':
        form = AMLForm(request.POST)
        if form.is_valid():
            aml_code_input = form.cleaned_data['aml']
            # Validate the OTP here (e.g., check if it matches the expected value)
            if validate_aml(aml_code_input, user_profile):  # Define this function based on your validation logic
                # Redirect to success page or dashboard
                return redirect('tac')
            else:
                form.add_error(None, 'Invalid AML code')
    else:
        form = AMLForm()

    context = {
        'user_profile': user_profile,
        'userprofile': userprofile,
        'form': form
    }
    return render(request, 'bank_app/aml.html', context)

@login_required
def tac(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # Handle the case where the profile doesn't exist
        user_profile = UserProfile.objects.create(user=request.user)

    # Check if the user is authenticated and try to get the user's profile
    if request.user.is_authenticated:
        try:
            userprofile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            # Handle the case where the UserProfile does not exist
            userprofile = None

    if request.method == 'POST':
        form = TACForm(request.POST)
        if form.is_valid():
            tac_code_input = form.cleaned_data['tac']
            # Validate the OTP here (e.g., check if it matches the expected value)
            if validate_tac(tac_code_input, user_profile):  # Define this function based on your validation logic
                # Redirect to success page or dashboard
                return redirect('vat')
            else:
                form.add_error(None, 'Invalid TAC code')
    else:
        form = TACForm()

    context = {
        'user_profile': user_profile,
        'userprofile': userprofile,
        'form': form
    }
    return render(request, 'bank_app/tac.html', context)

@login_required
def vat(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # Handle the case where the profile doesn't exist
        user_profile = UserProfile.objects.create(user=request.user)

    # Check if the user is authenticated and try to get the user's profile
    if request.user.is_authenticated:
        try:
            userprofile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            # Handle the case where the UserProfile does not exist
            userprofile = None

    if request.method == 'POST':
        form = VATForm(request.POST)
        if form.is_valid():
            vat_code_input = form.cleaned_data['vat']
            # Validate the OTP here (e.g., check if it matches the expected value)
            if validate_vat(vat_code_input, user_profile):  # Define this function based on your validation logic
                # Redirect to success page or dashboard
                return redirect('pending')
            else:
                form.add_error(None, 'Invalid VAT code')
    else:
        form = VATForm()

    context = {
        'user_profile': user_profile,
        'userprofile': userprofile,
        'form': form
    }
    return render(request, 'bank_app/vat.html', context)

@login_required
def imf(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # Handle the case where the profile doesn't exist
        user_profile = UserProfile.objects.create(user=request.user)

    # Check if the user is authenticated and try to get the user's profile
    if request.user.is_authenticated:
        try:
            userprofile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            # Handle the case where the UserProfile does not exist
            userprofile = None

    if request.method == 'POST':
        form = IMFForm(request.POST)
        if form.is_valid():
            imf_code_input = form.cleaned_data['imf']
            # Validate the OTP here (e.g., check if it matches the expected value)
            if validate_imf(imf_code_input, user_profile):  # Define this function based on your validation logic
                # Redirect to success page or dashboard
                return redirect('aml')
            else:
                form.add_error(None, 'Invalid IMF code')
    else:
        form = IMFForm()

    context = {
        'user_profile': user_profile,
        'userprofile': userprofile,
        'form': form
    }
    return render(request, 'bank_app/imf.html', context)

def reset_profile(request):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile(user=request.user)
        profile.save()

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('dashboard')  # Ensure 'dashboard' is a valid URL pattern
        else:
            print(form.errors)  # Log errors for debugging
    else:
        form = UserProfileForm(instance=profile)

    context = {'form': form}
    return render(request, 'bank_app/reset_profile.html', context)

@login_required
def pending(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # Handle the case where the profile doesn't exist
        user_profile = UserProfile.objects.create(user=request.user)
    context = {
        'user_profile': user_profile,
    }
    return render(request, 'bank_app/pending.html', context)

@login_required
def pendingPro(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # Handle the case where the profile doesn't exist
        user_profile = UserProfile.objects.create(user=request.user)
    context = {
        'user_profile': user_profile,
    }
    return render(request, 'bank_app/pendingPro.html', context)

@login_required
def kyc(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # Handle the case where the profile doesn't exist
        user_profile = UserProfile.objects.create(user=request.user)
    context = {
        'user_profile': user_profile,
    }
    return render(request, 'bank_app/kyc.html', context)

@login_required
def loans(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # Handle the case where the profile doesn't exist
        user_profile = UserProfile.objects.create(user=request.user)
    context = {
        'user_profile': user_profile,
    }
    return render(request, 'bank_app/loans.html', context)


def LogoutPage(request):
    logout(request)
    return redirect('reg')

