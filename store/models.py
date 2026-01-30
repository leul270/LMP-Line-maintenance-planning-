from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from datetime import timedelta
from django.dispatch import receiver
from django.db.models.signals import post_save
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)
# Custom User Model to match your registration form
class CustomUser(AbstractUser):
    # Override username field to use email
    username = None
    
    # Required fields from your registration form
    email = models.EmailField(unique=True, verbose_name='Primary Email')
    email2 = models.EmailField(blank=True, null=True, verbose_name='Secondary Email')
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50)
    company_id = models.CharField(max_length=100)
    
    # Authentication fields
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'company_id']
    
    objects = CustomUserManager()
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'


# UserProfile model
class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='profile'
    )
    email_notifications = models.BooleanField(default=True)
    timezone = models.CharField(max_length=50, default='UTC')
    
    def __str__(self):
        return f"Profile for {self.user.email}"


# Course Model
class Course(models.Model):
    COURSE_STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
        ('archived', 'Archived'),
    ]
    
    course_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='courses'
    )
    course_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    last_completed_date = models.DateField()
    interval_days = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Number of days between course completion and next due date"
    )
    due_date = models.DateField()
    next_reminder_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=COURSE_STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='course_images/', blank=True, null=True)
    
    class Meta:
        ordering = ['due_date']
    
    def __str__(self):
        return f"{self.course_name} - {self.user.email}"
    
    def get_image_url(self):
        """Return image URL or default image URL if no image exists"""
        try:
            if self.image and hasattr(self.image, 'url'):
                return self.image.url
        except (ValueError, AttributeError):
            pass
        # Return default image URL - adjust the path to your default image
        return '/static/images/placeholder.png'
    
    def save(self, *args, **kwargs):
        if not self.due_date and self.last_completed_date and self.interval_days:
            self.due_date = self.last_completed_date + timedelta(days=self.interval_days)
        
        today = timezone.now().date()
        if self.status != 'completed' and self.status != 'archived':
            if self.due_date < today:
                self.status = 'overdue'
            else:
                self.status = 'active'
        
        super().save(*args, **kwargs)
    
    def calculate_days_until_due(self):
        today = timezone.now().date()
        return (self.due_date - today).days
# Reminder Model
class Reminder(models.Model):
    REMINDER_TYPE_CHOICES = [
        ('60_days', '60 Days Before'),
        ('7_days', '7 Days Before'),
        ('3_days', '3 Days Before'),
        ('1_day', '1 Day Before'),
        ('due_today', 'Due Today'),
        ('overdue', 'Overdue'),
    ]
    
    REMINDER_STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    reminder_id = models.AutoField(primary_key=True)
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE, 
        related_name='reminders'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='reminders'
    )
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPE_CHOICES)
    scheduled_date = models.DateTimeField()
    sent_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=REMINDER_STATUS_CHOICES, default='scheduled')
    email_subject = models.CharField(max_length=255)
    email_body = models.TextField()
    retry_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['scheduled_date']
    
    def __str__(self):
        return f"Reminder {self.reminder_type} for {self.course.course_name}"
# ReminderLog Model - FIXED: NOT nested inside Reminder class
class ReminderLog(models.Model):
    DELIVERY_STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ]
    
    log_id = models.AutoField(primary_key=True)
    reminder = models.ForeignKey(
        Reminder, 
        on_delete=models.CASCADE, 
        related_name='logs'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='reminder_logs'
    )
    sent_at = models.DateTimeField()
    delivery_status = models.CharField(max_length=20, choices=DELIVERY_STATUS_CHOICES)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"Log {self.log_id} - {self.delivery_status} at {self.sent_at}"


# Signals - FIXED: Removed duplicate imports and function definitions
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)
class CourseTemplate(models.Model):
    COURSE_STATUS_CHOICES = [
        ('active', 'Active'),
        ('archived', 'Archived'),
    ]
    
    template_id = models.AutoField(primary_key=True)
    course_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    interval_days = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Number of days between course completion and next due date"
    )
    status = models.CharField(max_length=20, choices=COURSE_STATUS_CHOICES, default='active')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_courses'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='course_images/', blank=True, null=True)
    is_mandatory = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['course_name']
    
    def __str__(self):
        return f"{self.course_name}"

# User Course Instance Model
class UserCourse(models.Model):
    COURSE_STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
        ('archived', 'Archived'),
    ]
    
    user_course_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_courses'
    )
    course_template = models.ForeignKey(
        CourseTemplate,
        on_delete=models.CASCADE,
        related_name='user_instances'
    )
    last_completed_date = models.DateField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    next_reminder_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=COURSE_STATUS_CHOICES, default='assigned')
    assigned_date = models.DateField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_courses'
    )
    
    class Meta:
        ordering = ['due_date']
        unique_together = ['user', 'course_template']
    
    def __str__(self):
        return f"{self.user.email} - {self.course_template.course_name}"
    
    def save(self, *args, **kwargs):
        # Calculate due date when last_completed_date is set
        if self.last_completed_date and self.course_template.interval_days:
            self.due_date = self.last_completed_date + timedelta(days=self.course_template.interval_days)
    def get_image_url(self):
        """Return image URL or default image URL if no image exists"""
        try:
            if self.image and hasattr(self.image, 'url'):
                return self.image.url
        except (ValueError, AttributeError):
            pass
        # Return default image URL - adjust the path to your default image
        return '/static/images/placeholder.png'

        # ============================================================================
# AIRCRAFT MAINTENANCE MODELS
# ============================================================================

class AircraftManufacturer(models.Model):
    """Aircraft manufacturers like Boeing, Airbus, Bombardier, etc."""
    name = models.CharField(max_length=100, unique=True)
    country = models.CharField(max_length=100, blank=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class AircraftModelGroup(models.Model):
    """Groups like B737_MAX, A350, B787, etc."""
    AIRCRAFT_CATEGORY_CHOICES = [
        ('PASSENGER', 'Passenger'),
        ('CARGO', 'Cargo'),
        ('COMBINED', 'Combined Passenger/Cargo'),
        ('SPECIAL', 'Special Mission'),
    ]
    
    name = models.CharField(max_length=50, unique=True)  # B737_MAX, A350, etc.
    full_name = models.CharField(max_length=200)  # Boeing 737-8MAX, Airbus A350-900
    manufacturer = models.ForeignKey(AircraftManufacturer, on_delete=models.CASCADE)
    category = models.CharField(max_length=20, choices=AIRCRAFT_CATEGORY_CHOICES)
    icao_code = models.CharField(max_length=10, blank=True)
    iata_code = models.CharField(max_length=3, blank=True)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Aircraft Model Group"
    
    def __str__(self):
        return f"{self.name} - {self.full_name}"


class Aircraft(models.Model):
    """Individual aircraft with tail numbers"""
    AIRCRAFT_STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('MAINTENANCE', 'Under Maintenance'),
        ('STORED', 'Stored'),
        ('RETIRED', 'Retired'),
    ]
    
    model_group = models.ForeignKey(AircraftModelGroup, on_delete=models.CASCADE, 
                                   related_name='aircraft')
    tail_number = models.CharField(max_length=20, unique=True)  # ET-AVI, ET-AVJ, etc.
    registration = models.CharField(max_length=50, unique=True)
    serial_number = models.CharField(max_length=100, blank=True)
    msn = models.CharField(max_length=50, blank=True, verbose_name="Manufacturer Serial Number")
    engine_type = models.CharField(max_length=100, blank=True)
    year_of_manufacture = models.IntegerField(null=True, blank=True)
    date_of_delivery = models.DateField(null=True, blank=True)
    current_status = models.CharField(max_length=20, choices=AIRCRAFT_STATUS_CHOICES, default='ACTIVE')
    # maintenance_location = models.CharField(max_length=200, blank=True)
    last_maintenance_date = models.DateField(null=True, blank=True)
    # next_check_due = models.DateField(null=True, blank=True)
    # next_a_check_due = models.DateField(null=True, blank=True)
    # next_c_check_due = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    # Maintenix Integration Fields
    maintenix_inventory_id = models.CharField(max_length=255, unique=True, 
                                            help_text="Inventory ID from Maintenix system")
    maintenix_url_template = models.TextField(
        help_text="URL template for accessing aircraft in Maintenix. Use {inventory_id} as placeholder."
    )
    # last_scraped = models.DateTimeField(null=True, blank=True)
    
    active = models.BooleanField(default=True)
    # created_at = models.DateTimeField(auto_now_add=True)
    # updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['tail_number']
        verbose_name_plural = "Aircraft"
    
    def __str__(self):
        return f"{self.tail_number} - {self.model_group.name}"
    
    @property
    def full_name(self):
        return f"{self.tail_number} ({self.model_group.full_name})"
    
    @property
    def maintenix_url(self):
        """Generate the Maintenix URL for this aircraft"""
        if self.maintenix_url_template and self.maintenix_inventory_id:
            return self.maintenix_url_template.format(inventory_id=self.maintenix_inventory_id)
        return None
    
    # @property
    # def is_overdue_for_check(self):
    #     """Check if aircraft is overdue for any scheduled check"""
    #     if self.next_check_due:
    #         return self.next_check_due < timezone.now().date()
    #     return False
    
    @property
    def open_task_count(self):
        return self.open_tasks.filter(status='OPEN').count()
    
    @property
    def open_work_package_count(self):
        return self.work_packages.filter(status='OPEN').count()


class AircraftScrapingSession(models.Model):
    """Track scraping sessions for aircraft data"""
    SCRAPING_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('PARTIAL', 'Partially Completed'),
    ]
    
    session_id = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    aircraft = models.ForeignKey(Aircraft, on_delete=models.CASCADE, null=True, blank=True)
    aircraft_model_group = models.ForeignKey(AircraftModelGroup, on_delete=models.CASCADE, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=SCRAPING_STATUS_CHOICES, default='PENDING')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Statistics
    tasks_scraped = models.IntegerField(default=0)
    work_packages_scraped = models.IntegerField(default=0)
    errors_encountered = models.IntegerField(default=0)
    
    # Error tracking
    error_message = models.TextField(blank=True)
    log_file_path = models.CharField(max_length=500, blank=True)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"Scraping Session {self.session_id} - {self.get_status_display()}"
    
    @property
    def duration(self):
        if self.completed_at:
            return self.completed_at - self.started_at
        return None


class OpenTask(models.Model):
    """Open Tasks from Maintenix system"""
    TASK_STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('ON_HOLD', 'On Hold'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('DEFERRED', 'Deferred'),
    ]
    
    TASK_PRIORITY_CHOICES = [
        ('CRITICAL', 'Critical'),
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
        ('ROUTINE', 'Routine'),
    ]
    
    WORK_TYPE_CHOICES = [
        ('LINE', 'Line Maintenance'),
        ('HANGAR', 'Hangar Maintenance'),
        ('SHOP', 'Shop Maintenance'),
        ('INSPECTION', 'Inspection'),
        ('MODIFICATION', 'Modification'),
        ('TROUBLESHOOTING', 'Troubleshooting'),
        ('OTHER', 'Other'),
    ]
    
    # Core Task Information
    task_name = models.CharField(max_length=500)
    task_id = models.CharField(max_length=100, db_index=True)  # TSFN0045DQE
    config_position = models.CharField(max_length=200, blank=True)
    must_be_removed = models.BooleanField(default=False)
    due_date = models.DateTimeField(null=True, blank=True)
    soft_deadline = models.BooleanField(default=False)
    inventory = models.CharField(max_length=200)  # BOEING 737-8MAX - ET-AVI
    
    # Status and Classification
    task_status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='OPEN')
    work_type = models.CharField(max_length=20, choices=WORK_TYPE_CHOICES, default='LINE')
    originator = models.CharField(max_length=200, blank=True)
    task_priority = models.CharField(max_length=20, choices=TASK_PRIORITY_CHOICES, default='MEDIUM')
    schedule_priority = models.CharField(max_length=20, choices=TASK_PRIORITY_CHOICES, blank=True)
    
    # Driving Task Information
    driving_task_name = models.CharField(max_length=500, blank=True)
    driving_task_id = models.CharField(max_length=100, blank=True)
    etops_significant = models.BooleanField(default=False, verbose_name="ETOPS Significant")
    
    # Work Package Information
    work_package_name = models.CharField(max_length=500, blank=True)
    work_package_id = models.CharField(max_length=100, blank=True)
    work_package_number = models.CharField(max_length=100, blank=True)  # WO - 26538344
    
    # Aircraft Relationship
    aircraft = models.ForeignKey(Aircraft, on_delete=models.CASCADE, related_name='open_tasks')
    
    # Scraping Metadata
    scraped_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                  null=True, blank=True)
    scraped_session = models.ForeignKey(AircraftScrapingSession, on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name='scraped_tasks')
    scraped_at = models.DateTimeField(auto_now_add=True)
    
    # Additional Fields
    # created_in_maintenix = models.DateTimeField(null=True, blank=True)
    # last_modified_in_maintenix = models.DateTimeField(null=True, blank=True)
    # estimated_hours = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    # actual_hours = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    # notes = models.TextField(blank=True)
    
    # Deletion tracking
    marked_for_deletion = models.BooleanField(default=False)
    marked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                 null=True, blank=True, related_name='marked_tasks')
    marked_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['due_date', 'task_priority']
        indexes = [
            models.Index(fields=['task_id']),
            models.Index(fields=['task_status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['aircraft', 'task_status']),
        ]
        unique_together = ['aircraft', 'task_id']
    
    def __str__(self):
        return f"{self.task_name} - {self.task_id} ({self.aircraft.tail_number})"
    
    @property
    def is_overdue(self):
        if self.due_date:
            return self.due_date < timezone.now()
        return False
    
    @property
    def days_until_due(self):
        if self.due_date:
            delta = self.due_date - timezone.now()
            return delta.days
        return None
    
    @property
    def aircraft_tail_number(self):
        return self.aircraft.tail_number
    
    @property
    def aircraft_model(self):
        return self.aircraft.model_group.name


class OpenWorkPackage(models.Model):
    """Open Work Packages from Maintenix system"""
    WORK_PACKAGE_STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('ON_HOLD', 'On Hold'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('CLOSED', 'Closed'),
    ]
    
    WORK_PACKAGE_PRIORITY_CHOICES = [
        ('CRITICAL', 'Critical'),
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
    ]
    
    # Core Work Package Information
    work_package_name = models.CharField(max_length=500)
    work_package_id = models.CharField(max_length=100, db_index=True)  # TSFN0045DQE
    inventory = models.CharField(max_length=200)  # BOEING 737-8MAX - ET-AVI
    work_package_number = models.CharField(max_length=100)  # WO - 26538344
    work_package_status = models.CharField(max_length=20, choices=WORK_PACKAGE_STATUS_CHOICES, default='OPEN')
    request_parts = models.BooleanField(default=False, verbose_name="Request Parts Required")
    
    # Scheduling Information
    work_location = models.CharField(max_length=200, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    
    # Priority Information
    schedule_priority = models.CharField(max_length=20, choices=WORK_PACKAGE_PRIORITY_CHOICES, blank=True)
    
    # Task Information
    driving_task_name = models.CharField(max_length=500, blank=True)
    driving_task_id = models.CharField(max_length=100, blank=True)
    
    # Aircraft Relationship
    aircraft = models.ForeignKey(Aircraft, on_delete=models.CASCADE, related_name='work_packages')
    
    # Scraping Metadata
    scraped_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                  null=True, blank=True)
    scraped_session = models.ForeignKey(AircraftScrapingSession, on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name='scraped_work_packages')
    scraped_at = models.DateTimeField(auto_now_add=True)
    
    # Additional Fields
    # created_in_maintenix = models.DateTimeField(null=True, blank=True)
    # last_modified_in_maintenix = models.DateTimeField(null=True, blank=True)
    # estimated_duration_hours = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    # actual_duration_hours = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    # man_hours_estimated = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    # man_hours_actual = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    # notes = models.TextField(blank=True)
    
    # Deletion tracking
    marked_for_deletion = models.BooleanField(default=False)
    marked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                 null=True, blank=True, related_name='marked_work_packages')
    marked_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['start_date', 'schedule_priority']
        indexes = [
            models.Index(fields=['work_package_id']),
            models.Index(fields=['work_package_status']),
            models.Index(fields=['start_date']),
            models.Index(fields=['aircraft', 'work_package_status']),
        ]
        unique_together = ['aircraft', 'work_package_id']
    
    def __str__(self):
        return f"{self.work_package_name} - {self.work_package_number} ({self.aircraft.tail_number})"
    
    @property
    def is_active(self):
        return self.work_package_status in ['OPEN', 'IN_PROGRESS']
    
    @property
    def duration_days(self):
        if self.start_date and self.end_date:
            delta = self.end_date - self.start_date
            return delta.days
        return None
    
    @property
    def has_started(self):
        if self.start_date:
            return self.start_date <= timezone.now()
        return False
    
    @property
    def is_overdue(self):
        if self.end_date:
            return self.end_date < timezone.now() and self.is_active
        return False
    
    @property
    def associated_tasks(self):
        """Get tasks associated with this work package"""
        return OpenTask.objects.filter(
            work_package_id=self.work_package_id,
            aircraft=self.aircraft
        )
    
    @property
    def aircraft_tail_number(self):
        return self.aircraft.tail_number
    
    @property
    def aircraft_model(self):
        return self.aircraft.model_group.name


class AircraftAlert(models.Model):
    """Alerts for aircraft maintenance events"""
    ALERT_TYPE_CHOICES = [
        ('OVERDUE_TASK', 'Overdue Task'),
        ('OVERDUE_WORK_PACKAGE', 'Overdue Work Package'),
        ('UPCOMING_DUE_DATE', 'Upcoming Due Date'),
        ('CRITICAL_TASK', 'Critical Task'),
        ('AIRCRAFT_CHECK_DUE', 'Aircraft Check Due'),
        ('SYSTEM', 'System Alert'),
    ]
    
    ALERT_PRIORITY_CHOICES = [
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
    ]
    
    aircraft = models.ForeignKey(Aircraft, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPE_CHOICES)
    priority = models.CharField(max_length=10, choices=ALERT_PRIORITY_CHOICES, default='MEDIUM')
    title = models.CharField(max_length=200)
    message = models.TextField()
    related_task = models.ForeignKey(OpenTask, on_delete=models.SET_NULL, null=True, blank=True)
    related_work_package = models.ForeignKey(OpenWorkPackage, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Alert status
    is_active = models.BooleanField(default=True)
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                       null=True, blank=True, related_name='acknowledged_alerts')
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.aircraft.tail_number}"
    
    @property
    def days_since_created(self):
        return (timezone.now() - self.created_at).days


# class AircraftDashboardStats(models.Model):
#     """Dashboard statistics for quick access"""
#     aircraft = models.OneToOneField(Aircraft, on_delete=models.CASCADE, related_name='dashboard_stats')
    
#     # Counts
#     total_open_tasks = models.IntegerField(default=0)
#     overdue_tasks = models.IntegerField(default=0)
#     critical_tasks = models.IntegerField(default=0)
#     total_open_work_packages = models.IntegerField(default=0)
#     overdue_work_packages = models.IntegerField(default=0)
#     active_alerts = models.IntegerField(default=0)
    
    # # Dates
    # next_task_due_date = models.DateTimeField(null=True, blank=True)
    # next_work_package_start = models.DateTimeField(null=True, blank=True)
    
    # calculated_at = models.DateTimeField(auto_now=True)
    
    # class Meta:
    #     verbose_name = "Aircraft Dashboard Statistics"
    #     verbose_name_plural = "Aircraft Dashboard Statistics"
    
    # def __str__(self):
    #     return f"Stats for {self.aircraft.tail_number}"
    
    # def update_stats(self):
    #     """Update all statistics"""
    #     self.total_open_tasks = self.aircraft.open_tasks.filter(task_status='OPEN').count()
    #     self.overdue_tasks = self.aircraft.open_tasks.filter(
    #         task_status='OPEN',
    #         due_date__lt=timezone.now()
        # ).count()
        # self.critical_tasks = self.aircraft.open_tasks.filter(
        #     task_status='OPEN',
        #     task_priority='CRITICAL'
        # ).count()
        
        # self.total_open_work_packages = self.aircraft.work_packages.filter(
        #     work_package_status='OPEN'
        # ).count()
        # self.overdue_work_packages = self.aircraft.work_packages.filter(
        #     work_package_status='OPEN',
        #     end_date__lt=timezone.now()
        # ).count()
        
        # self.active_alerts = self.aircraft.alerts.filter(is_active=True, acknowledged=False).count()
        
        # # Get next due dates
        # next_task = self.aircraft.open_tasks.filter(
        #     task_status='OPEN',
        #     due_date__gte=timezone.now()
        # ).order_by('due_date').first()
        # if next_task:
        #     self.next_task_due_date = next_task.due_date
        
        # next_wp = self.aircraft.work_packages.filter(
        #     work_package_status='OPEN',
        #     start_date__gte=timezone.now()
        # ).order_by('start_date').first()
        # if next_wp:
        #     self.next_work_package_start = next_wp.start_date
        
        # self.save()


# ============================================================================
# SIGNALS
# ============================================================================

# @receiver(post_save, sender=Aircraft)
# def create_aircraft_dashboard_stats(sender, instance, created, **kwargs):
#     """Create dashboard stats when a new aircraft is created"""
#     if created:
#         AircraftDashboardStats.objects.create(aircraft=instance)


# @receiver(post_save, sender=OpenTask)
# @receiver(post_save, sender=OpenWorkPackage)
# def update_aircraft_stats(sender, instance, **kwargs):
#     """Update aircraft stats when tasks or work packages change"""
#     try:
#         stats = instance.aircraft.dashboard_stats
#         stats.update_stats()
#     except AircraftDashboardStats.DoesNotExist:
#         AircraftDashboardStats.objects.create(aircraft=instance.aircraft)


# @receiver(post_save, sender=OpenTask)
# def create_task_alerts(sender, instance, created, **kwargs):
#     """Create alerts for critical or overdue tasks"""
#     if instance.is_overdue and instance.task_status == 'OPEN':
#         AircraftAlert.objects.create(
#             aircraft=instance.aircraft,
#             alert_type='OVERDUE_TASK',
#             priority='HIGH' if instance.task_priority in ['CRITICAL', 'HIGH'] else 'MEDIUM',
#             title=f"Overdue Task: {instance.task_name}",
#             message=f"Task {instance.task_id} is overdue since {instance.due_date}",
#             related_task=instance
#         )
    
    # if instance.task_priority == 'CRITICAL' and instance.task_status == 'OPEN':
    #     AircraftAlert.objects.create(
    #         aircraft=instance.aircraft,
    #         alert_type='CRITICAL_TASK',
    #         priority='HIGH',
    #         title=f"Critical Task: {instance.task_name}",
    #         message=f"Critical task {instance.task_id} requires immediate attention",
    #         related_task=instance
    #     )


# @receiver(post_save, sender=OpenWorkPackage)
# def create_work_package_alerts(sender, instance, created, **kwargs):
#     """Create alerts for overdue work packages"""
#     if instance.is_overdue and instance.work_package_status == 'OPEN':
#         AircraftAlert.objects.create(
#             aircraft=instance.aircraft,
#             alert_type='OVERDUE_WORK_PACKAGE',
#             priority='HIGH' if instance.schedule_priority in ['CRITICAL', 'HIGH'] else 'MEDIUM',
#             title=f"Overdue Work Package: {instance.work_package_name}",
#             message=f"Work package {instance.work_package_number} is overdue since {instance.end_date}",
#             related_work_package=instance
#         )
class AircraftFlightSchedule(models.Model):
    """
    Model to store aircraft flight schedule data with only specified fields.
    """
    
    # Core identifying fields
    flight_date = models.DateField()
    
    # Previous Flight Information (from your list)
    previous_flight_number = models.CharField(max_length=10, blank=True, verbose_name="PFLT")
    previous_flight_location = models.CharField(max_length=3, blank=True, verbose_name="FROM")
    scheduled_arrival_time = models.TimeField(null=True, blank=True, verbose_name="STA")
    
    # Aircraft Equipment Information
    equipment_type = models.CharField(max_length=50, blank=True, verbose_name="EQPT")
    previous_tail_scheduled = models.CharField(max_length=20, blank=True, verbose_name="PTAIL")
    current_tail_scheduled = models.CharField(max_length=20, verbose_name="TAIL")
    
    # Current Flight Information
    current_flight_number = models.CharField(max_length=10, verbose_name="FLT")
    flight_destination = models.CharField(max_length=3, verbose_name="DEST")
    scheduled_departure_time = models.TimeField(null=True, blank=True, verbose_name="STD")
    
    # Link to existing Aircraft model (optional but useful for relationships)
    aircraft = models.ForeignKey('Aircraft', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='flight_schedules')
    
    # Scraping metadata (minimal)
    scraped_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['flight_date', 'scheduled_departure_time']
        verbose_name = "Aircraft Flight Schedule"
        verbose_name_plural = "Aircraft Flight Schedules"
        indexes = [
            models.Index(fields=['flight_date']),
            models.Index(fields=['current_tail_scheduled']),
            models.Index(fields=['current_flight_number']),
        ]
    
    def __str__(self):
        return f"{self.current_flight_number} - {self.current_tail_scheduled} ({self.flight_date})"
    
    def save(self, *args, **kwargs):
        # Auto-link to Aircraft model based on tail number if not already linked
        if self.current_tail_scheduled and not self.aircraft:
            try:
                aircraft = Aircraft.objects.filter(tail_number=self.current_tail_scheduled).first()
                if aircraft:
                    self.aircraft = aircraft
            except:
                pass  # Silently fail if aircraft not found
        
        super().save(*args, **kwargs)