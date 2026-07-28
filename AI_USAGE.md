# AI Usage and Project Setup Log

This document log details the use of AI tools, workflow steps, setup commands, and architectural decisions made during the development of the Box Selection System.

---

## 1. Project Context & AI Collaboration

### AI Tools Used
* **Gemini / AntiGravity**: documentation logging.
* **Gemini chat Secondary AI Assistant**: Used for project structure, boilerplate, and algorithmic/API code generation.

### Key Prompts & Workflow Log
1. **Setup & Environment**:
   * Initialized a Python virtual environment (`python3 -m venv venv`).
   * Installed `django` and `djangorestframework`.
   * Generated the root Django project `box_selection_system` in the current directory (`django-admin startproject box_selection_system .`).
   * Created the Django app `box_app`.
   * Added `rest_framework` and `box_app` to `INSTALLED_APPS` in `settings.py`.
   * Froze project dependencies into `requirements.txt`.
   * Ran initial SQLite database migrations.
2. **Data Models**:
   * Designed the database schema containing `Product`, `Box`, `Order`, and `OrderItem` models.
   * Utilized `DecimalField` and `MinValueValidator` to guarantee accurate calculations for spatial dimensions, volume, weight, and financial costs.
3. **Phase 2: Recommendation Engine (`services.py`)**:
   * Requested `box_app/services.py` containing `recommend_box_for_order()` with filters for max weight, volume, 3D sorted orientation fitting, and tie-breaking cost minimization.
4. **Phase 3: API Views, Serializers, and Routing**:
   * Prompted for `serializers.py` containing DRF serializers for `Product`, `Box`, `Order`, and a flexible request serializer (`BoxRecommendationRequestSerializer`).
   * Prompted for `views.py` with CRUD viewsets and a custom `@api_view(['POST'])` endpoint `/api/recommend-box/`.
   * Wired up application and project level `urls.py`.
5. **Phase 4: 3D Spatial Simulator Frontend & Interactive Dashboard**:
   * Prompted for a built-in HTML/CSS/JS frontend dashboard (`/api/simulator/`) leveraging Three.js to provide real-time 3D box packing visualization and live API endpoint testing.

## 2. Prompts 

1) : -📦 What the Project Is About
You are building an AI-Assisted Box Selection System for an e-commerce warehouse.
When customers buy items, the warehouse team needs to package them. To keep shipping efficient and safe, the system needs to evaluate available shipping boxes and automatically recommend the best box based on constraints.

📐 The Core Constraints
Dimensions & Volume: Each product and box has length, width, and height. Products must fit inside the box's internal dimensions.
Weight Limit: Products have weight, and each box has a max_weight capacity that cannot be exceeded.
Cost Optimization: Different boxes have different costs. Out of all the boxes that fit the items and safely support their weight, the system must choose the cheapest box.


TEST_OUTPUT.md or a GitHub Actions CI link showing tests passing , lets plan first 

2) prompt :-   *"I need to set up a new Django REST API project called box_selection_system using SQLite3. Can you give me the step-by-step terminal commands to:


Create a virtual environment (venv) and activate it.

Install Django and Django REST Framework (djangorestframework).

Create the main Django project structure inside my root directory.

Create a Django app named box_app and register it in settings.py.

Generate a requirements.txt file."* 

3) prompt - "Generate the box_app/models.py file with models for Product, Box, Order, and OrderItem.


Use DecimalField for precise dimensions (length, width, height), weight, and cost.

Include MinValueValidator to prevent zero or negative values.

Add @property helper methods on Product and Box to calculate volume.

Add helper methods on Order to calculate the total cumulative weight and total volume across all OrderItem items."* 

4) prompt - "Write a python service module in box_app/services.py for a box recommendation system.
Requirements:

Create a function recommend_box_for_order(order: Order) -> Optional[Box].
Filter out boxes where order.total_weight() exceeds box.max_weight.
Filter out boxes where order.total_volume() exceeds box.volume.
Ensure individual item dimensions fit inside the box by sorting dimensions (L, W, H) for both the product and the box to account for 3D rotation/orientation.
Out of all valid candidate boxes, return the one with the lowest cost. If no box fits, return None.
Include clear docstrings and typing annotations."*

5) prompt -  box_app/serializers.py using Django REST Framework (rest_framework.serializers).
Include serializers for:

ProductSerializer (all fields)
BoxSerializer (all fields + volume property)
OrderItemSerializer (include nested product details or product ID and quantity)
OrderSerializer (include nested items, total_weight, and total_volume)
A standalone BoxRecommendationRequestSerializer that accepts an order_id (IntegerField or UUID) OR a raw list of product items with quantities to request a recommendation directly."*

6) prompt - box_app/views.py file using Django REST Framework.

Create ModelViewSets or APIViews for managing Product, Box, and Order objects.
Create an @api_view(['POST']) endpoint named recommend_box_view or an APIView class /api/recommend-box/.
The view should accept an order_id in the request body, retrieve the Order instance, invoke recommend_box_for_order(order) from services.py, and return the recommended box details as JSON with HTTP status 200.
If no box is found, return {"message": "No suitable box found for this order."} with HTTP 404 or 200 depending on standard API design. Handle invalid order IDs cleanly with HTTP 400/404."*


---

## 3. Architectural & Content Decisions

### Accepted Output
* Default SQLite configuration in `settings.py` for simplicity and standard development testing.
* Basic setup shell commands and virtual environment workflows.
* Database model schemas including customized helper methods for volume calculation.
* Use of `select_related('product')` to eliminate N+1 DB queries in order statistics calculation.
* Dimension sorting (`sorted(product_dims)` vs `sorted(box_dims)`) to account for item 3D rotations during compatibility checks.
* Secondary sorting key (`b.cost, b.volume`) for tie-breaking identical box prices.
* Mutual exclusivity validation in `BoxRecommendationRequestSerializer` enforcing either `order_id` or raw `items`.
* DRF `ModelViewSet` instances for managing product and box inventories.
* Clean REST HTTP response status codes (HTTP 200, 400, 404).

### Rejected / Modified Output
* **Field Types**: Explicitly rejected using `FloatField` for dimensions, weights, and costs to prevent floating-point precision inaccuracies during candidate box evaluations. Instead, `DecimalField` was mandated.
* **Academic/Guidelines Compliance**: Refused AI generation for the personal reflection section ("What Did You Learn?") and raw chat export files as mandated by the project's submission guidelines.

### Human Optimizations & Edge Case Fixes
* **Mock Order Implementation**: Implemented an in-memory mock `Order` construct in `recommend_box_view` to calculate box fit for transient item sets without polluting the SQLite database with unsaved test orders.

### AI Mistakes & Hallucinations Identified
* **Missing Validators**: AI-generated model templates omitted necessary value constraints (manually resolved by importing and applying `MinValueValidator`).
* **Precision Control**: Initial AI suggestions had potential rounding errors in volume and weight comparison logic prior to applying explicit decimal precision controls.
* **Property Call Syntax**: Ensured `@property` calls on models (`order.total_weight`, `order.total_volume`) are called as properties rather than methods.

### AI Limitations
* **Multi-item 3D Stacking Heuristic**: The generated algorithm verifies individual item dimensional limits and overall aggregate volume/weight, but does not perform full spatial 3D bin packing layout for multiple items simultaneously. Highlighted this trade-off for human review.

---

## 4. Database Models (`box_app/models.py`)

Below is the Django database models implementation defining the core schema, validators, and helper properties.

```python
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator

# Common validator to ensure physical measurements are strictly positive (> 0)
POSITIVE_MIN_VALUE_VALIDATOR = [MinValueValidator(Decimal('0.01'))]


class Product(models.Model):
    """
    Represents an individual item that can be ordered.
    Dimensions are in centimeters (cm), weight in kilograms (kg).
    """
    name = models.CharField(max_length=255)
    length = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=POSITIVE_MIN_VALUE_VALIDATOR,
        help_text="Length in cm"
    )
    width = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=POSITIVE_MIN_VALUE_VALIDATOR,
        help_text="Width in cm"
    )
    height = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=POSITIVE_MIN_VALUE_VALIDATOR,
        help_text="Height in cm"
    )
    weight = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=POSITIVE_MIN_VALUE_VALIDATOR,
        help_text="Weight in kg"
    )

    @property
    def volume(self) -> Decimal:
        """Calculates volume in cubic centimeters (cm³)."""
        return self.length * self.width * self.height

    def __str__(self):
        return f"{self.name} ({self.length}x{self.width}x{self.height} cm)"


class Box(models.Model):
    """
    Represents a shipping container available in the warehouse.
    Internal dimensions in cm, max_weight capacity in kg, cost in currency units.
    """
    name = models.CharField(max_length=255)
    length = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=POSITIVE_MIN_VALUE_VALIDATOR,
        help_text="Internal length in cm"
    )
    width = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=POSITIVE_MIN_VALUE_VALIDATOR,
        help_text="Internal width in cm"
    )
    height = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=POSITIVE_MIN_VALUE_VALIDATOR,
        help_text="Internal height in cm"
    )
    max_weight = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=POSITIVE_MIN_VALUE_VALIDATOR,
        help_text="Maximum weight capacity in kg"
    )
    cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Cost of the box"
    )

    @property
    def volume(self) -> Decimal:
        """Calculates internal volume in cubic centimeters (cm³)."""
        return self.length * self.width * self.height

    def __str__(self):
        return f"{name} - ${cost} (Max Wt: {max_weight}kg)"


class Order(models.Model):
    """
    Represents a customer order containing one or more products via OrderItem.
    """
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_weight(self) -> Decimal:
        """Calculates total cumulative weight across all order items."""
        items = self.items.select_related('product')
        return sum((item.product.weight * item.quantity for item in items), Decimal('0.00'))

    @property
    def total_volume(self) -> Decimal:
        """Calculates total cumulative volume across all order items."""
        items = self.items.select_related('product')
        return sum((item.product.volume * item.quantity for item in items), Decimal('0.00'))

    def __str__(self):
        return f"Order #{self.id} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class OrderItem(models.Model):
    """
    Junction table representing products within a specific order and their quantities.
    """
    order = models.ForeignKey(
        Order, 
        related_name='items', 
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.PROTECT
    )
    quantity = models.PositiveIntegerField(
        default=1, 
        validators=[MinValueValidator(1)]
    )

    def __str__(self):
        return f"{self.quantity}x {self.product.name} (Order #{self.order.id})"
```

### Key Highlights
* **Validation**: `MinValueValidator(Decimal('0.01'))` is attached to all dimensional, weight, and quantity fields to prevent zero or negative values at both the DB and Form levels.
* **Precision**: All monetary and measurement values utilize `DecimalField` to eliminate floating-point rounding errors.
* **Performance Optimization**: The helper properties `total_weight` and `total_volume` utilize `.select_related('product')` to avoid N+1 database queries when iterating over `OrderItem` instances.

]

## Verification & Next Steps
* **Endpoint Routing Verification**: Verified that endpoint routes are successfully registered and accessible under `/api/products/`, `/api/boxes/`, `/api/orders/`, and `/api/recommend-box/`.
* **Database Verification**: Successfully ran migrations (`python manage.py migrate`) and verified server execution using `python manage.py runserver`.
* **Next Steps**: Moving to (Automated Unit Testing with Django TestCase).
run the command `python manage.py test` to verify that the models and views are functioning as expected.




# 5.What i learned from this project



1) use of serializer : - as serializer i have used mostly on high end project where we commnunicate between apps and database , to ensure the data pass with correct constraint and valid the data incoming , through json and if doesnt vaild we can shows 400 bad request , since i this data are highly in float and decimal strict validation is required , so i have used serializer to validate the data and also to convert the data into json format. 

2) as this project was just to showcase A recommendation system for box selection in the item with the box size are registred in Models , so with the use of serialize and Djnago orms i have inserted a single data and then after having test cases run according to our project states that recommends box with accoridng to data od box models present in DB , after that i wanted to simulate with 3D so i have tried to implement 3D rendering  frontend which shows accrding to the data of box models present in DB , and also i have used django rest framework for the api calls and also for the frontend to communicate with the backend and get the data from the backend and show it in the frontend.

3) after creating api endpoints i tried to test this api points with using POSTMAN with passing Request in body to check wethere i am getting  http 200 response back from api endpoint i have created 

4) This project didnt needed much higher library , with the views and calaculation able to predict accroding to the math of sizes and metrics data present , we provdide from services to views which is able to give response to the client , and using Sqlites3 without high database setting  or complex configuration , i am able to directly connect with local as django provides it 

5) i wanted to integrate a RAG based AI chat bot on this application which recommends accroding to data presnet in DB , by using langchain , lang graph and postgresql as database in vector embedding , it can automatcally suggest , but as our project and task mentioned i have followed only that , this are my personal recommandation feature which i would have intergrated if its requires , this project can have dashboard  , analytics , for warehouse team to check box qunatity and item size , by adding AI agent if warehouse teams has new item we can have our AI agent with personalizedd Function which automatically creates box without querying or need off adminstrator , and a notifation services for alert with using docker , kafka  , rabbitmq , and API gateway like KONG


## 6. AI mistakes 

1) i have used 2 AI chat from gemini  for coding , my maini motive was to use less tokens as possible , the app was well made , but AI got Hallucinations when creating 3D  box item simulator , where items are got overlapped out tof the box , i got that error by sending valid data from backend from serilaizer to frontend so that box shaoes as our data has 

2) it forgot too many conversation in the middle , but as i know the structure and it was easy for me to communicate with tools and get to my expected code and output fast as possible 
