#!/usr/bin/env python3
"""
Indian Food Menu Population Script
Populates the database with authentic Indian cuisine items
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from app import create_app
from models import db, Category, MenuItem
from datetime import datetime

def create_app_context():
    """Create Flask app context for database operations"""
    app = create_app()
    with app.app_context():
        return app

def create_categories():
    """Create Indian food categories"""
    categories = [
        {"name": "Appetizers", "description": "Traditional Indian starters and snacks"},
        {"name": "Curries", "description": "Authentic Indian curry dishes"},
        {"name": "Rice Dishes", "description": "Indian rice preparations and biryanis"},
        {"name": "Bread", "description": "Indian breads and flatbreads"},
        {"name": "Beverages", "description": "Traditional Indian drinks"},
        {"name": "Desserts", "description": "Authentic Indian sweets and desserts"},
        {"name": "Vegetarian", "description": "Pure vegetarian dishes"},
        {"name": "Vegan", "description": "Plant-based Indian dishes"},
        {"name": "Gluten-Free", "description": "Gluten-free Indian cuisine"},
        {"name": "Tandoor", "description": "Tandoor oven specialties"}
    ]
    
    created_categories = []
    for cat_data in categories:
        existing = Category.query.filter_by(name=cat_data["name"]).first()
        if not existing:
            category = Category.create_category(
                name=cat_data["name"],
                description=cat_data["description"]
            )
            created_categories.append(category)
            print(f"Created category: {category.name}")
        else:
            created_categories.append(existing)
            print(f"Category already exists: {existing.name}")
    
    return created_categories

def create_menu_items(categories):
    """Create Indian food menu items"""
    # Get category objects
    category_dict = {cat.name: cat for cat in categories}
    
    menu_items = [
        # Appetizers
        {
            "name": "Samosa",
            "description": "Crispy triangular pastries filled with spiced potatoes and peas",
            "price": 50.00,
            "category": "Appetizers",
            "stock_quantity": 100,
            "min_stock_level": 20,
            "image_path": "static/images/samosa.jpg",
            "spice_level": "Medium",
            "is_vegetarian": True,
            "is_vegan": False,
            "is_gluten_free": False,
            "cooking_time": 15,
            "difficulty": "Easy",
            "popularity_rating": 9,
            "calories": 180,
            "protein": 4,
            "carbs": 25,
            "fat": 7
        },
        {
            "name": "Aloo Tikki",
            "description": "Crispy potato patties served with chutneys",
            "price": 80.00,
            "category": "Appetizers",
            "stock_quantity": 80,
            "min_stock_level": 15,
            "image_path": "static/images/aloo_tikki.jpg",
            "spice_level": "Mild",
            "is_vegetarian": True,
            "is_vegan": True,
            "is_gluten_free": True,
            "cooking_time": 12,
            "difficulty": "Easy",
            "popularity_rating": 8,
            "calories": 150,
            "protein": 3,
            "carbs": 22,
            "fat": 5
        },
        {
            "name": "Chicken Tikka",
            "description": "Grilled marinated chicken pieces with aromatic spices",
            "price": 180.00,
            "category": "Appetizers",
            "stock_quantity": 60,
            "min_stock_level": 10,
            "image_path": "static/images/chicken_tikka.jpg",
            "spice_level": "Medium",
            "is_vegetarian": False,
            "is_vegan": False,
            "is_gluten_free": True,
            "cooking_time": 25,
            "difficulty": "Medium",
            "popularity_rating": 9,
            "calories": 220,
            "protein": 28,
            "carbs": 5,
            "fat": 12
        },
        
        # Curries
        {
            "name": "Butter Chicken",
            "description": "Creamy tomato-based curry with tender chicken pieces",
            "price": 280.00,
            "category": "Curries",
            "stock_quantity": 50,
            "min_stock_level": 10,
            "image_path": "static/images/butter_chicken.jpg",
            "spice_level": "Mild",
            "is_vegetarian": False,
            "is_vegan": False,
            "is_gluten_free": True,
            "cooking_time": 30,
            "difficulty": "Medium",
            "popularity_rating": 10,
            "calories": 350,
            "protein": 25,
            "carbs": 15,
            "fat": 24
        },
        {
            "name": "Dal Makhani",
            "description": "Rich and creamy black lentils slow-cooked in butter and cream",
            "price": 220.00,
            "category": "Curries",
            "stock_quantity": 40,
            "min_stock_level": 8,
            "image_path": "static/images/dal_makhani.jpg",
            "spice_level": "Mild",
            "is_vegetarian": True,
            "is_vegan": False,
            "is_gluten_free": True,
            "cooking_time": 45,
            "difficulty": "Medium",
            "popularity_rating": 9,
            "calories": 280,
            "protein": 12,
            "carbs": 35,
            "fat": 12
        },
        {
            "name": "Paneer Makhani",
            "description": "Cottage cheese in rich, creamy tomato gravy",
            "price": 250.00,
            "category": "Curries",
            "stock_quantity": 35,
            "min_stock_level": 8,
            "image_path": "static/images/paneer_makhani.jpg",
            "spice_level": "Mild",
            "is_vegetarian": True,
            "is_vegan": False,
            "is_gluten_free": True,
            "cooking_time": 25,
            "difficulty": "Easy",
            "popularity_rating": 9,
            "calories": 320,
            "protein": 18,
            "carbs": 12,
            "fat": 24
        },
        {
            "name": "Chicken Curry",
            "description": "Traditional chicken curry with onions, tomatoes, and spices",
            "price": 240.00,
            "category": "Curries",
            "stock_quantity": 45,
            "min_stock_level": 10,
            "image_path": "static/images/chicken_curry.jpg",
            "spice_level": "Medium",
            "is_vegetarian": False,
            "is_vegan": False,
            "is_gluten_free": True,
            "cooking_time": 35,
            "difficulty": "Medium",
            "popularity_rating": 8,
            "calories": 290,
            "protein": 26,
            "carbs": 8,
            "fat": 18
        },
        
        # Rice Dishes
        {
            "name": "Chicken Biryani",
            "description": "Fragrant basmati rice layered with spiced chicken and aromatic herbs",
            "price": 320.00,
            "category": "Rice Dishes",
            "stock_quantity": 30,
            "min_stock_level": 5,
            "image_path": "static/images/chicken_biryani.jpg",
            "spice_level": "Medium",
            "is_vegetarian": False,
            "is_vegan": False,
            "is_gluten_free": True,
            "cooking_time": 60,
            "difficulty": "Hard",
            "popularity_rating": 10,
            "calories": 450,
            "protein": 28,
            "carbs": 52,
            "fat": 15
        },
        {
            "name": "Mutton Biryani",
            "description": "Rich mutton biryani with tender meat and basmati rice",
            "price": 380.00,
            "category": "Rice Dishes",
            "stock_quantity": 25,
            "min_stock_level": 5,
            "image_path": "static/images/mutton_biryani.jpg",
            "spice_level": "Spicy",
            "is_vegetarian": False,
            "is_vegan": False,
            "is_gluten_free": True,
            "cooking_time": 90,
            "difficulty": "Hard",
            "popularity_rating": 9,
            "calories": 520,
            "protein": 32,
            "carbs": 48,
            "fat": 22
        },
        {
            "name": "Vegetable Biryani",
            "description": "Mixed vegetables cooked with basmati rice and authentic spices",
            "price": 240.00,
            "category": "Rice Dishes",
            "stock_quantity": 35,
            "min_stock_level": 8,
            "image_path": "static/images/veg_biryani.jpg",
            "spice_level": "Medium",
            "is_vegetarian": True,
            "is_vegan": True,
            "is_gluten_free": True,
            "cooking_time": 45,
            "difficulty": "Medium",
            "popularity_rating": 8,
            "calories": 350,
            "protein": 8,
            "carbs": 65,
            "fat": 8
        },
        
        # Bread
        {
            "name": "Butter Naan",
            "description": "Soft, pillowy bread brushed with butter",
            "price": 60.00,
            "category": "Bread",
            "stock_quantity": 120,
            "min_stock_level": 30,
            "image_path": "static/images/butter_naan.jpg",
            "spice_level": "Mild",
            "is_vegetarian": True,
            "is_vegan": False,
            "is_gluten_free": False,
            "cooking_time": 8,
            "difficulty": "Medium",
            "popularity_rating": 9,
            "calories": 280,
            "protein": 8,
            "carbs": 45,
            "fat": 8
        },
        {
            "name": "Garlic Naan",
            "description": "Traditional naan bread topped with fresh garlic and herbs",
            "price": 55.00,
            "category": "Bread",
            "stock_quantity": 100,
            "min_stock_level": 25,
            "image_path": "static/images/garlic_naan.jpg",
            "spice_level": "Mild",
            "is_vegetarian": True,
            "is_vegan": False,
            "is_gluten_free": False,
            "cooking_time": 8,
            "difficulty": "Medium",
            "popularity_rating": 8,
            "calories": 270,
            "protein": 8,
            "carbs": 43,
            "fat": 7
        },
        {
            "name": "Tandoori Roti",
            "description": "Whole wheat bread baked in tandoor oven",
            "price": 40.00,
            "category": "Bread",
            "stock_quantity": 80,
            "min_stock_level": 20,
            "image_path": "static/images/tandoori_roti.jpg",
            "spice_level": "Mild",
            "is_vegetarian": True,
            "is_vegan": True,
            "is_gluten_free": False,
            "cooking_time": 6,
            "difficulty": "Easy",
            "popularity_rating": 7,
            "calories": 180,
            "protein": 6,
            "carbs": 32,
            "fat": 3
        },
        
        # Beverages
        {
            "name": "Mango Lassi",
            "description": "Refreshing yogurt drink with sweet mango flavor",
            "price": 80.00,
            "category": "Beverages",
            "stock_quantity": 60,
            "min_stock_level": 15,
            "image_path": "static/images/mango_lassi.jpg",
            "spice_level": "Mild",
            "is_vegetarian": True,
            "is_vegan": False,
            "is_gluten_free": True,
            "cooking_time": 3,
            "difficulty": "Easy",
            "popularity_rating": 9,
            "calories": 150,
            "protein": 5,
            "carbs": 25,
            "fat": 4
        },
        {
            "name": "Sweet Lassi",
            "description": "Traditional sweet yogurt drink with cardamom",
            "price": 70.00,
            "category": "Beverages",
            "stock_quantity": 50,
            "min_stock_level": 12,
            "image_path": "static/images/sweet_lassi.jpg",
            "spice_level": "Mild",
            "is_vegetarian": True,
            "is_vegan": False,
            "is_gluten_free": True,
            "cooking_time": 3,
            "difficulty": "Easy",
            "popularity_rating": 8,
            "calories": 120,
            "protein": 4,
            "carbs": 20,
            "fat": 3
        },
        {
            "name": "Masala Chai",
            "description": "Spiced Indian tea with milk and aromatic spices",
            "price": 40.00,
            "category": "Beverages",
            "stock_quantity": 100,
            "min_stock_level": 25,
            "image_path": "static/images/masala_chai.jpg",
            "spice_level": "Medium",
            "is_vegetarian": True,
            "is_vegan": False,
            "is_gluten_free": True,
            "cooking_time": 5,
            "difficulty": "Easy",
            "popularity_rating": 8,
            "calories": 80,
            "protein": 3,
            "carbs": 8,
            "fat": 4
        },
        
        # Desserts
        {
            "name": "Gulab Jamun",
            "description": "Soft, spongy milk dumplings in sugar syrup",
            "price": 90.00,
            "category": "Desserts",
            "stock_quantity": 40,
            "min_stock_level": 10,
            "image_path": "static/images/gulab_jamun.jpg",
            "spice_level": "Mild",
            "is_vegetarian": True,
            "is_vegan": False,
            "is_gluten_free": True,
            "cooking_time": 20,
            "difficulty": "Medium",
            "popularity_rating": 9,
            "calories": 200,
            "protein": 4,
            "carbs": 35,
            "fat": 6
        },
        {
            "name": "Kulfi",
            "description": "Traditional Indian ice cream with cardamom and pistachios",
            "price": 70.00,
            "category": "Desserts",
            "stock_quantity": 30,
            "min_stock_level": 8,
            "image_path": "static/images/kulfi.jpg",
            "spice_level": "Mild",
            "is_vegetarian": True,
            "is_vegan": False,
            "is_gluten_free": True,
            "cooking_time": 240,
            "difficulty": "Hard",
            "popularity_rating": 8,
            "calories": 180,
            "protein": 5,
            "carbs": 20,
            "fat": 10
        },
        {
            "name": "Ras Malai",
            "description": "Cottage cheese dumplings in sweetened milk",
            "price": 110.00,
            "category": "Desserts",
            "stock_quantity": 25,
            "min_stock_level": 5,
            "image_path": "static/images/ras_malai.jpg",
            "spice_level": "Mild",
            "is_vegetarian": True,
            "is_vegan": False,
            "is_gluten_free": True,
            "cooking_time": 45,
            "difficulty": "Hard",
            "popularity_rating": 9,
            "calories": 220,
            "protein": 8,
            "carbs": 25,
            "fat": 12
        },
        
        # Tandoor Specialties
        {
            "name": "Tandoori Chicken",
            "description": "Whole chicken marinated in yogurt and spices, grilled in tandoor",
            "price": 450.00,
            "category": "Tandoor",
            "stock_quantity": 15,
            "min_stock_level": 3,
            "image_path": "static/images/tandoori_chicken.jpg",
            "spice_level": "Medium",
            "is_vegetarian": False,
            "is_vegan": False,
            "is_gluten_free": True,
            "cooking_time": 45,
            "difficulty": "Hard",
            "popularity_rating": 10,
            "calories": 380,
            "protein": 45,
            "carbs": 8,
            "fat": 18
        },
        {
            "name": "Paneer Tikka",
            "description": "Cottage cheese cubes marinated and grilled in tandoor",
            "price": 220.00,
            "category": "Tandoor",
            "stock_quantity": 35,
            "min_stock_level": 8,
            "image_path": "static/images/paneer_tikka.jpg",
            "spice_level": "Medium",
            "is_vegetarian": True,
            "is_vegan": False,
            "is_gluten_free": True,
            "cooking_time": 20,
            "difficulty": "Medium",
            "popularity_rating": 9,
            "calories": 280,
            "protein": 18,
            "carbs": 8,
            "fat": 20
        },
        
        # Vegetarian Specialties
        {
            "name": "Chole Bhature",
            "description": "Spicy chickpeas served with fluffy deep-fried bread",
            "price": 180.00,
            "category": "Vegetarian",
            "stock_quantity": 40,
            "min_stock_level": 10,
            "image_path": "static/images/chole_bhature.jpg",
            "spice_level": "Spicy",
            "is_vegetarian": True,
            "is_vegan": False,
            "is_gluten_free": False,
            "cooking_time": 30,
            "difficulty": "Medium",
            "popularity_rating": 9,
            "calories": 420,
            "protein": 15,
            "carbs": 55,
            "fat": 16
        },
        {
            "name": "Palak Paneer",
            "description": "Cottage cheese in creamy spinach gravy",
            "price": 240.00,
            "category": "Vegetarian",
            "stock_quantity": 35,
            "min_stock_level": 8,
            "image_path": "static/images/palak_paneer.jpg",
            "spice_level": "Mild",
            "is_vegetarian": True,
            "is_vegan": False,
            "is_gluten_free": True,
            "cooking_time": 25,
            "difficulty": "Medium",
            "popularity_rating": 8,
            "calories": 290,
            "protein": 16,
            "carbs": 12,
            "fat": 22
        }
    ]
    
    created_items = []
    for item_data in menu_items:
        existing = MenuItem.query.filter_by(name=item_data["name"]).first()
        if not existing:
            category = category_dict.get(item_data["category"])
            if category:
                menu_item = MenuItem.create_menu_item(
                    name=item_data["name"],
                    price=item_data["price"],
                    category_id=category.id,
                    description=item_data["description"],
                    stock_quantity=item_data["stock_quantity"],
                    min_stock_level=item_data["min_stock_level"],
                    image_path=item_data["image_path"]
                )
                
                # Add extended attributes
                menu_item.spice_level = item_data.get("spice_level", "Mild")
                menu_item.is_vegetarian = item_data.get("is_vegetarian", True)
                menu_item.is_vegan = item_data.get("is_vegan", False)
                menu_item.is_gluten_free = item_data.get("is_gluten_free", False)
                menu_item.cooking_time = item_data.get("cooking_time", 15)
                menu_item.difficulty = item_data.get("difficulty", "Medium")
                menu_item.popularity_rating = item_data.get("popularity_rating", 5)
                menu_item.calories = item_data.get("calories", 0)
                menu_item.protein = item_data.get("protein", 0)
                menu_item.carbs = item_data.get("carbs", 0)
                menu_item.fat = item_data.get("fat", 0)
                
                db.session.commit()
                created_items.append(menu_item)
                print(f"Created menu item: {menu_item.name}")
            else:
                print(f"Category not found: {item_data['category']}")
        else:
            created_items.append(existing)
            print(f"Menu item already exists: {existing.name}")
    
    return created_items

def populate_indian_menu():
    """Main function to populate Indian menu"""
    app = create_app()
    
    with app.app_context():
        print("Starting Indian menu population...")
        
        try:
            # Create categories
            print("\n=== Creating Categories ===")
            categories = create_categories()
            
            # Create menu items
            print("\n=== Creating Menu Items ===")
            menu_items = create_menu_items(categories)
            
            print(f"\n=== Summary ===")
            print(f"Total categories created/found: {len(categories)}")
            print(f"Total menu items created/found: {len(menu_items)}")
            print("Indian menu population completed successfully!")
            
        except Exception as e:
            print(f"Error during population: {str(e)}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    try:
        populate_indian_menu()
    except Exception as e:
        print(f"Failed to populate Indian menu: {str(e)}")
        sys.exit(1)