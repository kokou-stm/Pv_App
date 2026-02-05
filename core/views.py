from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from .forms import UserRegistrationForm
from .models import Service, User



def register(request):
    """
    Vue d'inscription pour les nouveaux utilisateurs.
    """
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                'Votre compte a été créé avec succès ! '
                'Veuillez attendre la validation par un administrateur avant de vous connecter.'
            )
            return redirect('login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'registration/register.html', {'form': form})


def login_view(request):
    """
    Vue de connexion personnalisée qui vérifie si l'utilisateur est validé.
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_validated:
                login(request, user)
                messages.success(request, f'Bienvenue, {user.username} !')
                return redirect('dashboard')
            else:
                messages.error(
                    request,
                    'Votre compte est en attente de validation par un administrateur. '
                    'Vous recevrez un email une fois votre compte validé.'
                )
                return render(request, 'registration/pending_validation.html')
        else:
            messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect.')
    
    return render(request, 'registration/login.html')


def logout_view(request):
    """
    Vue de déconnexion.
    """
    logout(request)
    messages.success(request, 'Vous avez été déconnecté avec succès.')
    return redirect('login')


@login_required
def dashboard(request):
    """
    Tableau de bord pour les utilisateurs validés.
    """
    # Get user's current active service
    active_service = Service.objects.filter(
        user=request.user,
        statut='ouvert'
    ).first()
    
    # Get user's service history (last 5 services)
    service_history = Service.objects.filter(
        user=request.user
    ).order_by('-date_ouverture')[:5]
    
    return render(request, 'dashboard.html', {
        'user': request.user,
        'active_service': active_service,
        'service_history': service_history,
    })


def home(request):
    """
    Page d'accueil.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


@login_required
def open_service(request):
    """
    Ouvrir un nouveau service pour l'utilisateur.
    """
    # Check if user already has an active service
    active_service = Service.objects.filter(
        user=request.user,
        statut='ouvert'
    ).first()
    
    if active_service:
        messages.error(
            request,
            'Vous avez déjà un service actif. '
            'Veuillez fermer votre service actuel avant d\'en ouvrir un nouveau.'
        )
        return redirect('dashboard')
    
    # Create new service
    try:
        service = Service(user=request.user)
        service.full_clean()  # Validate before saving
        service.save()
        messages.success(
            request,
            f'Service ouvert avec succès ! '
            f'Fermeture automatique le {service.date_fermeture.strftime("%d/%m/%Y à %H:%M")}.'
        )
    except ValidationError as e:
        messages.error(request, str(e))
    
    return redirect('dashboard')


@login_required
def close_service(request):
    """
    Fermer le service actif de l'utilisateur.
    """
    active_service = Service.objects.filter(
        user=request.user,
        statut='ouvert'
    ).first()
    
    if not active_service:
        messages.error(request, 'Vous n\'avez pas de service actif à fermer.')
        return redirect('dashboard')
    
    active_service.close_service()
    messages.success(request, 'Service fermé avec succès.')
    
    return redirect('dashboard')


# Validation views
@login_required
def validate_action(request, action_id):
    """
    Valider une action (admin only).
    """
    from .models import Action, Validation
    
    # Check permission
    if request.user.role != 'admin':
        messages.error(request, 'Seuls les administrateurs peuvent valider des actions.')
        return redirect('dashboard')
    
    # Get action
    try:
        action = Action.objects.get(id=action_id)
    except Action.DoesNotExist:
        messages.error(request, 'Action introuvable.')
        return redirect('pending_validations')
    
    # Check if already validated
    if action.validation_status == 'validé':
        messages.warning(request, 'Cette action est déjà validée.')
        return redirect('pending_validations')
    
    # Warn if self-validation
    if action.auteur == request.user:
        messages.warning(
            request,
            f'⚠️ Auto-validation détectée : vous validez votre propre action.'
        )
    
    # Create validation
    Validation.objects.create(
        action=action,
        validateur=request.user,
        statut='validé'
    )
    
    messages.success(request, f'Action #{action.id} validée avec succès.')
    return redirect('pending_validations')


@login_required
def reject_action(request, action_id):
    """
    Refuser une action avec commentaire (admin only).
    """
    from .models import Action, Validation
    
    # Check permission
    if request.user.role != 'admin':
        messages.error(request, 'Seuls les administrateurs peuvent refuser des actions.')
        return redirect('dashboard')
    
    # Get action
    try:
        action = Action.objects.get(id=action_id)
    except Action.DoesNotExist:
        messages.error(request, 'Action introuvable.')
        return redirect('pending_validations')
    
    if request.method == 'POST':
        commentaire = request.POST.get('commentaire', '').strip()
        
        if not commentaire:
            messages.error(request, 'Un commentaire est obligatoire pour refuser une action.')
            return render(request, 'validations/reject.html', {'action': action})
        
        # Create validation
        try:
            validation = Validation(
                action=action,
                validateur=request.user,
                statut='refusé',
                commentaire=commentaire
            )
            validation.full_clean()
            validation.save()
            
            messages.success(request, f'Action #{action.id} refusée avec succès.')
            return redirect('pending_validations')
        except ValidationError as e:
            messages.error(request, str(e))
    
    return render(request, 'validations/reject.html', {'action': action})


@login_required
def comment_action(request, action_id):
    """
    Commenter une action sans changer le statut (admin only).
    """
    from .models import Action, Validation
    
    # Check permission
    if request.user.role != 'admin':
        messages.error(request, 'Seuls les administrateurs peuvent commenter des actions.')
        return redirect('dashboard')
    
    # Get action
    try:
        action = Action.objects.get(id=action_id)
    except Action.DoesNotExist:
        messages.error(request, 'Action introuvable.')
        return redirect('pending_validations')
    
    if request.method == 'POST':
        commentaire = request.POST.get('commentaire', '').strip()
        
        if not commentaire:
            messages.error(request, 'Un commentaire est requis.')
            return render(request, 'validations/comment.html', {'action': action})
        
        # Create validation with current status
        Validation.objects.create(
            action=action,
            validateur=request.user,
            statut=action.validation_status,  # Keep current status
            commentaire=commentaire
        )
        
        messages.success(request, f'Commentaire ajouté à l\'action #{action.id}.')
        return redirect('pending_validations')
    
    return render(request, 'validations/comment.html', {'action': action})


@login_required
def pending_validations(request):
    """
    Liste des actions en attente de validation (admin only).
    """
    from .models import Action
    
    # Check permission
    if request.user.role != 'admin':
        messages.error(request, 'Seuls les administrateurs peuvent accéder à cette page.')
        return redirect('dashboard')
    
    # Get all actions pending validation
    actions = Action.objects.all()
    pending_actions = [action for action in actions if action.validation_status == 'en_attente']
    
    return render(request, 'validations/pending.html', {
        'pending_actions': pending_actions,
        'total_count': len(pending_actions)
    })


@login_required
def validation_history(request, action_id):
    """
    Historique des validations pour une action.
    """
    from .models import Action
    
    try:
        action = Action.objects.get(id=action_id)
    except Action.DoesNotExist:
        messages.error(request, 'Action introuvable.')
        return redirect('dashboard')
    
    # Check permission: author or admin
    if action.auteur != request.user and request.user.role != 'admin':
        messages.error(request, 'Vous n\'avez pas accès à cet historique.')
        return redirect('dashboard')
    
    validations = action.get_validation_history()
    
    return render(request, 'validations/history.html', {
        'action': action,
        'validations': validations
    })


# Consultation views
@login_required
def global_actions_view(request):
    """
    Vue globale des actions avec filtres.
    Accessible à tous les utilisateurs validés.
    """
    from .models import Action, User, Service
    from django.core.paginator import Paginator
    
    # Get all actions
    actions = Action.objects.select_related('auteur', 'service').all()
    
    # Apply filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    user_filter = request.GET.get('user')
    status_filter = request.GET.get('status')
    service_filter = request.GET.get('service')
    
    if date_from:
        actions = actions.filter(date_creation__gte=date_from)
    if date_to:
        actions = actions.filter(date_creation__lte=date_to)
    if user_filter:
        actions = actions.filter(auteur__id=user_filter)
    if status_filter:
        # Filter by validation status
        actions = [action for action in actions if action.validation_status == status_filter]
    if service_filter:
        actions = actions.filter(service__id=service_filter)
    
    # Pagination
    paginator = Paginator(actions if isinstance(actions, list) else actions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    users = User.objects.filter(is_validated=True).order_by('username')
    services = Service.objects.all().order_by('-date_ouverture')[:50]
    
    return render(request, 'consultation/actions.html', {
        'page_obj': page_obj,
        'users': users,
        'services': services,
        'filters': {
            'date_from': date_from,
            'date_to': date_to,
            'user': user_filter,
            'status': status_filter,
            'service': service_filter,
        }
    })


@login_required
def global_services_view(request):
    """
    Vue globale des services avec filtres.
    """
    from .models import Service, User
    from django.core.paginator import Paginator
    from django.db.models import Count
    
    # Get all services with action count
    services = Service.objects.select_related('user').annotate(
        action_count=Count('actions')
    ).all()
    
    # Apply filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    user_filter = request.GET.get('user')
    status_filter = request.GET.get('status')
    
    if date_from:
        services = services.filter(date_ouverture__gte=date_from)
    if date_to:
        services = services.filter(date_ouverture__lte=date_to)
    if user_filter:
        services = services.filter(user__id=user_filter)
    if status_filter:
        services = services.filter(statut=status_filter)
    
    # Pagination
    paginator = Paginator(services, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    users = User.objects.filter(is_validated=True).order_by('username')
    
    # Calculate statistics
    total_services = services.count()
    open_services = services.filter(statut='ouvert').count()
    closed_services = services.filter(statut='fermé').count()
    
    return render(request, 'consultation/services.html', {
        'page_obj': page_obj,
        'users': users,
        'filters': {
            'date_from': date_from,
            'date_to': date_to,
            'user': user_filter,
            'status': status_filter,
        },
        'stats': {
            'total': total_services,
            'open': open_services,
            'closed': closed_services,
        }
    })


@login_required
def global_validations_view(request):
    """
    Vue globale des validations (admin/validator only).
    """
    from .models import Validation, User
    from django.core.paginator import Paginator
    
    # Check permission
    if request.user.role not in ['admin', 'validator']:
        messages.error(request, 'Accès réservé aux administrateurs et validateurs.')
        return redirect('dashboard')
    
    # Get all validations
    validations = Validation.objects.select_related(
        'action', 'action__auteur', 'validateur'
    ).all()
    
    # Apply filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    validator_filter = request.GET.get('validator')
    status_filter = request.GET.get('status')
    author_filter = request.GET.get('author')
    
    if date_from:
        validations = validations.filter(date_validation__gte=date_from)
    if date_to:
        validations = validations.filter(date_validation__lte=date_to)
    if validator_filter:
        validations = validations.filter(validateur__id=validator_filter)
    if status_filter:
        validations = validations.filter(statut=status_filter)
    if author_filter:
        validations = validations.filter(action__auteur__id=author_filter)
    
    # Pagination
    paginator = Paginator(validations, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    validators = User.objects.filter(role__in=['admin', 'validator']).order_by('username')
    authors = User.objects.filter(is_validated=True).order_by('username')
    
    # Calculate statistics
    total_validations = validations.count()
    validated_count = validations.filter(statut='validé').count()
    rejected_count = validations.filter(statut='refusé').count()
    
    return render(request, 'consultation/validations.html', {
        'page_obj': page_obj,
        'validators': validators,
        'authors': authors,
        'filters': {
            'date_from': date_from,
            'date_to': date_to,
            'validator': validator_filter,
            'status': status_filter,
            'author': author_filter,
        },
        'stats': {
            'total': total_validations,
            'validated': validated_count,
            'rejected': rejected_count,
            'approval_rate': (validated_count / total_validations * 100) if total_validations > 0 else 0,
        }
    })


@login_required
def user_profile_view(request, username=None):
    """
    Vue du profil utilisateur avec historique complet.
    """
    from .models import User, Service, Action
    from django.shortcuts import get_object_or_404
    from datetime import timedelta
    
    # Determine which user's profile to show
    if username:
        profile_user = get_object_or_404(User, username=username)
    else:
        profile_user = request.user
    
    # Check permission
    if profile_user != request.user and request.user.role != 'admin':
        messages.error(request, 'Vous ne pouvez voir que votre propre profil.')
        return redirect('user_profile', username=request.user.username)
    
    # Get service history
    services = Service.objects.filter(user=profile_user).order_by('-date_ouverture')
    
    # Get action history
    actions = Action.objects.filter(auteur=profile_user).select_related('service').order_by('-date_creation')
    
    # Apply action filters
    action_status_filter = request.GET.get('action_status')
    action_date_from = request.GET.get('action_date_from')
    action_date_to = request.GET.get('action_date_to')
    
    if action_status_filter:
        actions = [action for action in actions if action.validation_status == action_status_filter]
    if action_date_from:
        actions = actions.filter(date_creation__gte=action_date_from) if not isinstance(actions, list) else [a for a in actions if a.date_creation.date() >= action_date_from]
    if action_date_to:
        actions = actions.filter(date_creation__lte=action_date_to) if not isinstance(actions, list) else [a for a in actions if a.date_creation.date() <= action_date_to]
    
    # Calculate statistics
    total_services = services.count()
    total_service_time = timedelta()
    for service in services.filter(statut='fermé'):
        if service.date_fermeture:
            total_service_time += (service.date_fermeture - service.date_ouverture)
    
    total_actions = len(actions) if isinstance(actions, list) else actions.count()
    validated_actions = len([a for a in actions if a.validation_status == 'validé']) if isinstance(actions, list) else sum(1 for a in actions if a.validation_status == 'validé')
    rejected_actions = len([a for a in actions if a.validation_status == 'refusé']) if isinstance(actions, list) else sum(1 for a in actions if a.validation_status == 'refusé')
    
    validation_rate = (validated_actions / total_actions * 100) if total_actions > 0 else 0
    
    return render(request, 'profile/user_profile.html', {
        'profile_user': profile_user,
        'services': services[:10],  # Last 10 services
        'actions': actions[:20] if isinstance(actions, list) else actions[:20],  # Last 20 actions
        'stats': {
            'total_services': total_services,
            'total_service_hours': total_service_time.total_seconds() / 3600,
            'avg_service_hours': (total_service_time.total_seconds() / 3600 / total_services) if total_services > 0 else 0,
            'total_actions': total_actions,
            'validated_actions': validated_actions,
            'rejected_actions': rejected_actions,
            'pending_actions': total_actions - validated_actions - rejected_actions,
            'validation_rate': validation_rate,
        },
        'filters': {
            'action_status': action_status_filter,
            'action_date_from': action_date_from,
            'action_date_to': action_date_to,
        }
    })


# Notification views
@login_required
def notifications_list(request):
    """
    Liste des notifications de l'utilisateur.
    """
    from .models import Notification
    from django.core.paginator import Paginator
    
    # Get all notifications for the user
    notifications = Notification.objects.filter(destinataire=request.user)
    
    # Apply filters
    type_filter = request.GET.get('type')
    status_filter = request.GET.get('status')
    
    if type_filter:
        notifications = notifications.filter(type=type_filter)
    if status_filter == 'lue':
        notifications = notifications.filter(lue=True)
    elif status_filter == 'non_lue':
        notifications = notifications.filter(lue=False)
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    total_count = Notification.objects.filter(destinataire=request.user).count()
    unread_count = Notification.objects.filter(destinataire=request.user, lue=False).count()
    
    return render(request, 'notifications/list.html', {
        'page_obj': page_obj,
        'total_count': total_count,
        'unread_count': unread_count,
        'filters': {
            'type': type_filter,
            'status': status_filter,
        }
    })


@login_required
def mark_notification_read(request, notif_id):
    """
    Marquer une notification comme lue.
    """
    from .models import Notification
    from django.shortcuts import get_object_or_404
    
    notification = get_object_or_404(Notification, id=notif_id, destinataire=request.user)
    notification.lue = True
    notification.save()
    
    # Redirect to the related object if available
    next_url = request.GET.get('next', 'notifications_list')
    if notification.action:
        return redirect('global_actions_view')
    return redirect(next_url)


@login_required
def mark_all_notifications_read(request):
    """
    Marquer toutes les notifications comme lues.
    """
    from .models import Notification
    
    updated = Notification.objects.filter(destinataire=request.user, lue=False).update(lue=True)
    messages.success(request, f'{updated} notification(s) marquée(s) comme lue(s).')
    
    return redirect('notifications_list')


@login_required
def delete_notification(request, notif_id):
    """
    Supprimer une notification.
    """
    from .models import Notification
    from django.shortcuts import get_object_or_404
    
    notification = get_object_or_404(Notification, id=notif_id, destinataire=request.user)
    notification.delete()
    
    messages.success(request, 'Notification supprimée.')
    return redirect('notifications_list')


@login_required
def get_unread_count(request):
    """
    API JSON pour obtenir le nombre de notifications non lues.
    """
    from .models import Notification
    from django.http import JsonResponse
    
    count = Notification.objects.filter(destinataire=request.user, lue=False).count()
    return JsonResponse({'unread_count': count})


# ============================================================================
# GESTION DES ACTIONS
# ============================================================================

@login_required
def action_create(request):
    """
    Vue pour créer une nouvelle action.
    Vérifie qu'un service est actif avant de permettre la création.
    """
    from .forms import ActionForm
    from .models import Action, Service
    from django.utils import timezone
    
    # Vérifier si l'utilisateur a un service actif
    active_service = Service.objects.filter(
        user=request.user,
        statut='ouvert',
        date_fermeture__gt=timezone.now()
    ).first()
    
    if not active_service:
        messages.warning(
            request,
            'Vous devez avoir un service actif pour créer une action. '
            'Veuillez d\'abord ouvrir un service.'
        )
        return redirect('service_open')
    
    if request.method == 'POST':
        form = ActionForm(request.POST)
        if form.is_valid():
            action = form.save(commit=False)
            action.auteur = request.user
            action.service = active_service
            action.save()
            
            messages.success(
                request,
                f'Action créée avec succès ! '
                f'Les administrateurs ont été notifiés.'
            )
            return redirect('action_list')
    else:
        form = ActionForm()
    
    context = {
        'form': form,
        'active_service': active_service,
    }
    return render(request, 'actions/create.html', context)


@login_required
def action_list(request):
    """
    Vue pour afficher la liste des actions de l'utilisateur.
    """
    from .models import Action, Service, Validation
    from django.utils import timezone
    from django.core.paginator import Paginator
    from django.db.models import Q, Exists, OuterRef
    
    # Récupérer toutes les actions de l'utilisateur
    actions = Action.objects.filter(auteur=request.user).order_by('-date_creation')
    
    # Vérifier si l'utilisateur a un service actif
    active_service = Service.objects.filter(
        user=request.user,
        statut='ouvert',
        date_fermeture__gt=timezone.now()
    ).first()
    
    # Pagination
    paginator = Paginator(actions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistiques - calculées manuellement car validation_status est une propriété
    total_actions = actions.count()
    validated_actions = 0
    pending_actions = 0
    rejected_actions = 0
    
    for action in actions:
        status = action.validation_status
        if status == 'validé':
            validated_actions += 1
        elif status == 'refusé':
            rejected_actions += 1
        else:
            pending_actions += 1
    
    context = {
        'page_obj': page_obj,
        'active_service': active_service,
        'total_actions': total_actions,
        'validated_actions': validated_actions,
        'pending_actions': pending_actions,
        'rejected_actions': rejected_actions,
    }
    return render(request, 'actions/list.html', context)


@login_required
def action_edit(request, action_id):
    """
    Vue pour modifier une action existante.
    Uniquement possible si :
    - L'utilisateur est l'auteur
    - Le service est encore actif
    - L'action n'est pas validée
    """
    from .forms import ActionForm
    from .models import Action, Service
    from django.utils import timezone
    from django.shortcuts import get_object_or_404
    
    action = get_object_or_404(Action, id=action_id)
    
    # Vérifier que l'utilisateur est l'auteur
    if action.auteur != request.user:
        messages.error(request, 'Vous ne pouvez modifier que vos propres actions.')
        return redirect('action_list')
    
    # Vérifier que le service est encore actif
    if action.service.statut != 'ouvert' or action.service.date_fermeture <= timezone.now():
        messages.error(
            request,
            'Vous ne pouvez plus modifier cette action car le service est fermé.'
        )
        return redirect('action_list')
    
    # Vérifier que l'action n'est pas validée
    if action.validation_status == 'validé':
        messages.error(
            request,
            'Vous ne pouvez pas modifier une action déjà validée.'
        )
        return redirect('action_list')
    
    if request.method == 'POST':
        form = ActionForm(request.POST, instance=action)
        if form.is_valid():
            form.save()
            messages.success(request, 'Action modifiée avec succès !')
            return redirect('action_list')
    else:
        form = ActionForm(instance=action)
    
    context = {
        'form': form,
        'action': action,
        'is_edit': True,
    }
    return render(request, 'actions/edit.html', context)


# ============================================================================
# USER MENTION API
# ============================================================================

@login_required
def user_search_api(request):
    """
    API endpoint to search users for @mention autocomplete.
    Returns JSON list of users matching the query.
    """
    query = request.GET.get('q', '').strip()
    
    if not query:
        # Return all validated users if no query
        users = User.objects.filter(is_validated=True).order_by('username')[:10]
    else:
        # Search by username (case-insensitive)
        users = User.objects.filter(
            username__istartswith=query,
            is_validated=True
        ).order_by('username')[:10]
    
    # Format response
    user_list = [{
        'id': user.id,
        'username': user.username,
        'role': user.role,
        'role_display': user.get_role_display()
    } for user in users]
    
    return JsonResponse({'users': user_list})
