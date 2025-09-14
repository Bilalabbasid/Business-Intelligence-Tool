from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal
import logging

from .models import Sales, Customer, StaffPerformance, Inventory
from core.models import User

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Sales)
def update_customer_data_on_sale(sender, instance, created, **kwargs):
    """
    Update customer data when a new sale is created
    """
    if created and instance.customer:
        try:
            customer = instance.customer
            
            # Update customer statistics
            customer.total_spent += instance.total_amount
            customer.visit_count += 1
            customer.last_visit = instance.date
            
            # Add loyalty points (1 point per dollar spent)
            loyalty_points = int(instance.total_amount)
            customer.add_loyalty_points(loyalty_points)
            
            customer.save(update_fields=['total_spent', 'visit_count', 'last_visit'])
            
            logger.info(f"Updated customer {customer.customer_id} data after sale {instance.sale_id}")
            
        except Exception as e:
            logger.error(f"Error updating customer data for sale {instance.sale_id}: {str(e)}")


@receiver(post_save, sender=Sales)
def update_staff_performance_on_sale(sender, instance, created, **kwargs):
    """
    Update staff performance metrics when a sale is made
    """
    if created and instance.served_by:
        try:
            # Find or create today's performance record
            performance, created_perf = StaffPerformance.objects.get_or_create(
                staff=instance.served_by,
                branch=instance.branch,
                shift_date=instance.date.date(),
                defaults={
                    'shift_start': instance.date.time(),
                    'shift_end': instance.date.time(),
                    'hours_worked': Decimal('8.00'),  # Default 8-hour shift
                    'sales_generated': Decimal('0.00'),
                    'orders_served': 0,
                }
            )
            
            # Update performance metrics
            performance.sales_generated += instance.total_amount
            performance.orders_served += 1
            performance.save(update_fields=['sales_generated', 'orders_served', 'updated_at'])
            
            logger.info(f"Updated staff performance for {instance.served_by.username} after sale {instance.sale_id}")
            
        except Exception as e:
            logger.error(f"Error updating staff performance for sale {instance.sale_id}: {str(e)}")


@receiver(post_save, sender=Sales)
def update_inventory_on_sale(sender, instance, created, **kwargs):
    """
    Update inventory quantities when items are sold
    """
    if created and instance.items:
        try:
            for item_data in instance.items:
                # Try to find matching inventory item
                inventory_items = Inventory.objects.filter(
                    branch=instance.branch,
                    item_name__iexact=item_data.item_name,
                    is_active=True
                )
                
                for inventory_item in inventory_items:
                    # Reduce stock quantity
                    if inventory_item.stock_quantity >= item_data.quantity:
                        inventory_item.stock_quantity -= Decimal(str(item_data.quantity))
                        inventory_item.save(update_fields=['stock_quantity', 'last_updated'])
                        
                        # Log if item is now low stock
                        if inventory_item.is_low_stock:
                            logger.warning(f"Item {inventory_item.item_name} at {inventory_item.branch.name} is now low stock")
                    else:
                        logger.warning(f"Insufficient stock for {item_data.item_name} at {instance.branch.name}")
            
            logger.info(f"Updated inventory after sale {instance.sale_id}")
            
        except Exception as e:
            logger.error(f"Error updating inventory for sale {instance.sale_id}: {str(e)}")


@receiver(pre_save, sender=Customer)
def generate_customer_id(sender, instance, **kwargs):
    """
    Generate customer ID if not provided
    """
    if not instance.customer_id:
        # Generate customer ID based on phone number or timestamp
        if instance.phone:
            instance.customer_id = f"CUST_{instance.phone[-4:]}{int(timezone.now().timestamp())}"
        else:
            instance.customer_id = f"CUST_{int(timezone.now().timestamp())}"


@receiver(pre_save, sender=Sales)
def generate_sale_id(sender, instance, **kwargs):
    """
    Generate sale ID if not provided
    """
    if not instance.sale_id:
        # Generate sale ID with branch prefix and timestamp
        branch_prefix = instance.branch.branch_id[:3].upper() if instance.branch else "GEN"
        instance.sale_id = f"{branch_prefix}_{instance.date.strftime('%Y%m%d')}_{int(timezone.now().timestamp() * 1000) % 100000}"


@receiver(pre_save, sender=Inventory)
def generate_inventory_id(sender, instance, **kwargs):
    """
    Generate inventory ID if not provided
    """
    if not instance.inventory_id:
        # Generate inventory ID with branch and category prefix
        branch_prefix = instance.branch.branch_id[:3].upper() if instance.branch else "GEN"
        category_prefix = instance.category[:3].upper() if instance.category else "ITM"
        instance.inventory_id = f"{branch_prefix}_{category_prefix}_{int(timezone.now().timestamp())}"


@receiver(post_save, sender=Inventory)
def check_inventory_alerts(sender, instance, created, **kwargs):
    """
    Check and log inventory alerts
    """
    try:
        if instance.is_low_stock:
            logger.warning(
                f"LOW STOCK ALERT: {instance.item_name} at {instance.branch.name} "
                f"(Current: {instance.stock_quantity}, Reorder Level: {instance.reorder_level})"
            )
        
        if instance.is_expired:
            logger.error(
                f"EXPIRED ITEM ALERT: {instance.item_name} at {instance.branch.name} "
                f"expired on {instance.expiry_date}"
            )
    
    except Exception as e:
        logger.error(f"Error checking inventory alerts for {instance.inventory_id}: {str(e)}")


@receiver(post_save, sender=User)
def create_branch_for_manager(sender, instance, created, **kwargs):
    """
    Handle manager assignment to branches
    """
    if instance.role == User.MANAGER and instance.branch_id:
        try:
            from .models import Branch
            
            # Check if branch exists, if not create a placeholder
            branch_exists = Branch.objects.filter(branch_id=instance.branch_id).exists()
            
            if not branch_exists:
                logger.info(f"Creating placeholder branch {instance.branch_id} for manager {instance.username}")
                # This would typically be handled by proper branch creation workflow
                
        except Exception as e:
            logger.error(f"Error handling branch for manager {instance.username}: {str(e)}")