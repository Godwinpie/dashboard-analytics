# views.py
from django.views.generic import View
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import authenticate, logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.core.mail import  EmailMultiAlternatives
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


from django.template.loader import render_to_string
from django.conf import settings
import secrets
import string
from .forms import UserChartAccessForm
from .models import UserChartAccess


class LoginView(View):
    """User login view - Email based"""
    
    def get(self, request):
        # Redirect if already logged in
        if request.user.is_authenticated:
            return redirect('dashboard')
        
        return render(request, 'login.html')
    
    def post(self, request):
        email = request.POST.get('username')  # name="username" in form
        password = request.POST.get('password')
        
        if not email or not password:
            messages.error(request, 'Please provide both email and password')
            return render(request, 'login.html')
        
        # Authenticate using email (custom backend handles it)
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            login(request, user)
            
            # Get user's actual username or email for display
            display_name = user.get_full_name() or user.username or user.email
            messages.success(request, f'Welcome back, {display_name}!')
            
            # Redirect to next page or dashboard
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid email or password')
            return render(request, 'login.html')


class LogoutView(LoginRequiredMixin, View):
    """User logout view"""
    
    def get(self, request):
        username = request.user.username
        messages.success(request, f'Goodbye, {username}! You have been logged out.')
        logout(request)
        return redirect('users:login')


class InviteUserView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Invite new user API - Only superuser can access. Returns JSON for modal."""
    
    login_url = 'users:login'
    
    def test_func(self):
        """Check if user is superuser"""
        return self.request.user.is_superuser
    
    def handle_no_permission(self):
        """Return JSON error for unauthorized access"""
        return JsonResponse({
            'success': False,
            'message': 'You do not have permission to invite users'
        }, status=403)
    
    def post(self, request):
        """Process invite and send email - Returns JSON for modal"""
        email = request.POST.get('email', '').strip()
        chart_access = request.POST.getlist('chart_access')

        if not email:
            return JsonResponse({
                'success': False,
                'message': 'Email address is required'
            }, status=400)

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'success': False,
                'message': f'User with email {email} already exists'
            }, status=400)

        try:
            # Generate random password
            password = self.generate_password()

            # Create username from email
            username = email.split('@')[0]
            base_username = username
            counter = 1

            # Ensure unique username
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            # Create new user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )

            # Save chart access permissions
            UserChartAccess.objects.create(user=user, charts=chart_access)

            # Send welcome email with credentials
            self.send_invite_email(email, password, request)

            return JsonResponse({
                'success': True,
                'message': f'Invitation sent to {email}!'
            })

        except Exception as e:
            # If user was created but email failed, still inform about partial success
            if 'Failed to send email' in str(e):
                return JsonResponse({
                    'success': True,
                    'message': f'User {email} created but email could not be sent. Please share credentials manually.'
                })
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=500)
    
    def generate_password(self, length=12):
        """Generate secure random password"""
        # Characters to use in password
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = '@#$%&*'
        
        # Ensure at least one of each type
        password = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
            secrets.choice(special)
        ]
        
        # Fill the rest randomly
        all_chars = lowercase + uppercase + digits + special
        password += [secrets.choice(all_chars) for _ in range(length - 4)]
        
        # Shuffle to randomize positions
        secrets.SystemRandom().shuffle(password)
        
        return ''.join(password)
    
    def send_invite_email(self, email, password, request):
        """Send invitation email using HTML template"""
        # Build URLs
        login_url = request.build_absolute_uri(reverse('users:login'))
        dashboard_url = request.build_absolute_uri(reverse('dashboard'))
        
        # Get inviter name
        inviter_name = request.user.get_full_name() or request.user.email or request.user.username
        
        # Context for template
        context = {
            'inviter_name': inviter_name,
            'user_email': email,
            'user_password': password,
            'login_url': login_url,
            'dashboard_url': dashboard_url,
        }
        
        # Render HTML email template
        html_message = render_to_string('emails/invite_user.html', context)
        
        # Plain text fallback
        text_message = f"""
Welcome to Campaign Analytics!

You have been invited by {inviter_name} to join the Creative Performance Dashboard.

Your login credentials:
Email: {email}
Password: {password}

Login here: {login_url}

Please change your password after your first login.

Best regards,
Campaign Analytics Team
        """
        
        # Email subject
        subject = 'Welcome to Halasmile Creative Analytics'
        
        # Create email message with HTML alternative
        email_msg = EmailMultiAlternatives(
            subject=subject,
            body=text_message.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email]
        )
        
        # Attach HTML version
        email_msg.attach_alternative(html_message, "text/html")
        
        try:
            # Send email
            email_msg.send(fail_silently=False)
        except Exception as e:
            raise Exception(f'Failed to send email: {str(e)}')


class ManageUsersListView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Admin can see all users and manage their chart access"""
    login_url = 'users:login'

    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request):
        # Only show active users (soft delete filter)
        users = User.objects.filter(is_active=True).order_by('username')
        return render(request, 'manage_users_list.html', {'users': users})


class ManageUserAccessView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Admin can manage chart access for any user"""
    login_url = 'users:login'

    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        chart_access, _ = UserChartAccess.objects.get_or_create(user=user)
        form = UserChartAccessForm(instance=chart_access)
        return render(request, 'manage_user_access.html', {'form': form, 'managed_user': user})

    def post(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        chart_access, _ = UserChartAccess.objects.get_or_create(user=user)
        form = UserChartAccessForm(request.POST, instance=chart_access)
        if form.is_valid():
            form.save()
            messages.success(request, f'Chart access updated for {user.email or user.username}')
            return redirect('users:manage_users_list')
        return render(request, 'manage_user_access.html', {'form': form, 'managed_user': user})


class RemoveUserAPIView(LoginRequiredMixin, UserPassesTestMixin, View):
    """API endpoint for soft deleting users - Returns JSON"""
    login_url = 'users:login'

    def test_func(self):
        """Check if user is superuser"""
        return self.request.user.is_superuser

    def post(self, request, user_id):
        """Soft delete user by setting is_active to False"""
        try:
            user = get_object_or_404(User, id=user_id)
            
            # Prevent deleting yourself
            if user.id == request.user.id:
                return JsonResponse({
                    'success': False,
                    'message': 'You cannot remove yourself from the system'
                }, status=400)
            
            # Soft delete by setting is_active to False
            user.is_active = False
            user.save()
            
            return JsonResponse({
                'success': True,
                'message': f'User {user.email or user.username} has been removed from the system'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)

