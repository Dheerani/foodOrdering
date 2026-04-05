from django.contrib import admin
from .models import Product, ProductMetaInformation, ProductImages

admin.site.register(Product)
admin.site.register(ProductMetaInformation)
admin.site.register(ProductImages)