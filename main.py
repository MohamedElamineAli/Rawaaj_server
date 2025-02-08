from supabase import create_client, Client
import json
import uuid
import base64
from fastapi import FastAPI, HTTPException, UploadFile, File

SUPABASE_URL = "https://nigwgfryuxzcbelpbasz.supabase.co"
SUPABASE_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5pZ3dnZnJ5dXh6Y2JlbHBiYXN6Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNTQyMjYwNCwiZXhwIjoyMDUwOTk4NjA0fQ.UE3cOGKsNVp-Xn32Z27PRFOMAQJsE_YUxDhw-VuP5WA"

def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_API_KEY)

supabase = get_supabase_client()
app = FastAPI()

async def upload_image(file: UploadFile, bucket_name: str):
    try:
        # Generate a unique filename
        unique_filename = f"{uuid.uuid4()}-{file.filename}"

        # Read the file content
        file_content = await file.read()

        # Upload file to Supabase Storage
        response = supabase.storage.from_(bucket_name).upload(
            unique_filename,
            file_content,
            file_options={"content-type": file.content_type}
        )

        return {"message": "Image uploaded successfully", "filename": unique_filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {e}")


async def download_image(file_name: str, bucket_name: str):
    try:
        response = supabase.storage.from_(bucket_name).download(file_name)

        image_base64 = base64.b64encode(response).decode("utf-8")

        return {"message": "Image downloaded successfully", "image_content": image_base64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download image: {e}")

async def add_outfit(outfit_data: dict):
    try:
        # Insert the outfit into the `outfits` table
        outfit_response = supabase.table("outfits").insert({
            "user_id": outfit_data.get("user_id"),
            "outfit_image": outfit_data.get("outfit_image"),
            "total_price": outfit_data.get("total_price"),
            "num_of_likes": outfit_data.get("num_of_likes"),
            "description": outfit_data.get("description"),
        }).execute()

        outfit_id = outfit_response.data[0]["id"]

        # Insert the associated products into the `outfit_products` table
        for product_id in outfit_data.get("outfit_components", []):
            supabase.table("outfit_products").insert({
                "outfit_id": outfit_id,
                "product_id": product_id,
            }).execute()

        return {"outfit_id": outfit_id}
    except Exception as e:
        return {"error": str(e)}

async def get_outfit_by_id(outfit_id: int):
    try:
        # Fetch outfit details
        response = supabase.table("outfits").select("*, outfit_likes(*)").eq("id", outfit_id).execute()

        if not response.data:
            return {"error": "Outfit not found"}

        outfit = response.data[0]

        # Check if the outfit is liked
        likes = outfit.get("outfit_likes", [])
        is_liked = len(likes) > 0

        # Fetch associated products
        outfit_products_response = supabase.table("outfit_products").select("product_id").eq("outfit_id", outfit_id).execute()
        product_ids = [item["product_id"] for item in outfit_products_response.data]

        return {
            "id": outfit["id"],
            "outfit_image": outfit.get("outfit_image", ""),
            "total_price": outfit["total_price"],
            "num_of_likes": outfit.get("num_of_likes", 0),
            "is_liked": is_liked,
            "description": outfit["description"],
            "outfit_components": product_ids
        }
    except Exception as e:
        return {"error": str(e)}


async def get_all_outfits():
    try:
        response = supabase.table("outfits").select('*, outfit_likes(*)').execute()

        outfits = []
        for item in response.data:
            outfit_image = item.get("outfit_image", "")
            num_of_likes = item.get("num_of_likes", 0)
            likes = item.get("outfit_likes", [])
            is_liked = len(likes) > 0
            

            outfits.append({
                "id": item["id"],
                "outfit_image": outfit_image,
                "total_price": item["total_price"],
                "num_of_likes": num_of_likes,
                "is_liked": is_liked,
            })

        return {"outfits": outfits}
    except Exception as e:
        return {"error": str(e)}

async def get_outfits_by_context_type(context_type: str, user_id: int):
    try:
        if context_type == "history":
            response = supabase.table("outfit_history").select('*, outfits(*)') \
                .eq("user_id", user_id) \
                .order("visited_at", desc=True) \
                .execute()
        elif context_type == "isLiked":
            response = supabase.table("outfit_likes").select('*, outfits(*)') \
                .eq("user_id", user_id) \
                .execute()
        else:
            return {"error": "Invalid context type"}

        outfits = []
        seen_outfit_ids = set()

        for item in response.data:
            outfit = item["outfits"] if context_type in ["history", "isLiked"] else item

            if outfit["id"] in seen_outfit_ids:
                continue
            seen_outfit_ids.add(outfit["id"])

            outfits.append({
                "id": outfit["id"],
                "outfit_image": outfit.get("outfit_image", ""),
                "total_price": outfit["total_price"],
                "num_of_likes": outfit.get("num_of_likes", 0),
                "is_liked": context_type == "isLiked",
            })

        return {"outfits": outfits}
    except Exception as e:
        return {"error": str(e)}


async def search_outfits_by_description(keyword: str):
    try:
        response = supabase.table("outfits") \
            .select("*, outfit_likes(*)") \
            .ilike("description", f"*{keyword}*") \
            .limit(10) \
            .execute()

        outfits = []
        for item in response.data:
            outfit_image = item.get("outfit_image", "")
            num_of_likes = item.get("num_of_likes", 0)
            likes = item.get("outfit_likes", [])
            is_liked = len(likes) > 0

            outfits.append({
                "id": item["id"],
                "outfit_image": outfit_image,
                "total_price": item["total_price"],
                "num_of_likes": num_of_likes,
                "is_liked": is_liked,
                "description": item["description"],
            })

        return {"outfits": outfits}
    except Exception as e:
        return {"error": str(e)}



async def get_outfits_by_filters(size_id_list=None, color_id_list=None, price_range=None, price_order_type=None):
    try:
        # Step 1: Get product IDs that match the filters
        products_response = await get_products_by_filters(size_id_list, color_id_list)
        product_ids = [product['id'] for product in products_response['products']]

        # Step 2: Get outfit IDs that contain these products
        outfit_ids_response = supabase.table("outfit_products") \
            .select("outfit_id") \
            .in_("product_id", product_ids) \
            .execute()
        
        outfit_ids = list(set([outfit['outfit_id'] for outfit in outfit_ids_response.data]))  # Remove duplicates

        # Step 3: Query outfits with the filtered outfit IDs
        query = supabase.table("outfits").select("*, outfit_likes(*)").in_("id", outfit_ids)

        # Step 4: Filter by outfit total price
        if price_range:
            min_price, max_price = price_range
            query = query.gte("total_price", min_price).lte("total_price", max_price)

        # Step 5: Order outfits by price
        if price_order_type == "asc":
            query = query.order("total_price", desc=False)
        elif price_order_type == "desc":
            query = query.order("total_price", desc=True)

        response = query.execute()

        # Step 6: Process and return outfits
        outfits = []
        for item in response.data:
            outfit_image = item.get("outfit_image", "")
            num_of_likes = item.get("num_of_likes", 0)
            likes = item.get("outfit_likes", [])
            is_liked = len(likes) > 0

            outfits.append({
                "id": item["id"],
                "outfit_image": outfit_image,
                "total_price": item["total_price"],
                "num_of_likes": num_of_likes,
                "is_liked": is_liked,
                "description": item["description"],
            })

        return {"outfits": outfits}
    except Exception as e:
        return {"error": str(e)}


async def toggle_outfit_like(user_id: int, outfit_id: int):
    try:
        # Check if the like already exists
        response = supabase.table("outfit_likes") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("outfit_id", outfit_id) \
            .execute()

        if response.data:
            # If the like exists, remove it (unlike action)
            supabase.table("outfit_likes") \
                .delete() \
                .eq("user_id", user_id) \
                .eq("outfit_id", outfit_id) \
                .execute()
            return {"message": "Outfit unliked", "liked": False}
        else:
            # If the like doesn't exist, add it
            supabase.table("outfit_likes") \
                .insert({"user_id": user_id, "outfit_id": outfit_id}) \
                .execute()
            return {"message": "Outfit liked", "liked": True}
    except Exception as e:
        print(e)
        return {"error": str(e)}

async def track_outfit_visit(user_id: int, outfit_id: int):
    try:
        supabase.table("outfit_history").insert({
            "user_id": user_id,
            "outfit_id": outfit_id,
        }).execute()
        return {"message": "Outfit visit recorded"}
    except Exception as e:
        return {"error": str(e)}

async def update_outfit_image(outfit_id: int, new_outfit_image: str):
    try:
        # Update the outfit image in the 'outfits' table
        update_response = supabase.table("outfits").update({
            "outfit_image": new_outfit_image
        }).eq("id", outfit_id).execute()

        print(update_response)

        return {"message": "Outfit image updated successfully"}
    except Exception as e:
        return {"error": str(e)}

async def add_product(product_data: dict):
    try:
        # Insert the product into the `products` table
        product_response = supabase.table("products").insert({
            "category_id": product_data.get("category_id"),
            "shop_id": product_data.get("shop_id"),
            "price": product_data.get("price"),
            "description": product_data.get("description"),
            "total_ratings": product_data.get("total_ratings"),
            "materials": json.dumps(product_data.get("materials", [])),
            "origin": product_data.get("origin"),
        }).execute()

        product_id = product_response.data[0]["id"]

        # Insert sizes, colors, and images
        for size_id in product_data.get("sizes", []):
            supabase.table("product_sizes").insert({
                "product_id": product_id,
                "size_id": size_id,
            }).execute()

        for color_id in product_data.get("colors", []):
            supabase.table("product_colors").insert({
                "product_id": product_id,
                "color_id": color_id,
            }).execute()

        for image_url in product_data.get("images", []):
            supabase.table("product_images").insert({
                "product_id": product_id,
                "link": image_url,
            }).execute()

        return {"product_id": product_id}
    except Exception as e:
        print(e)
        return {"error": str(e)}

async def get_product_by_id(product_id: int):
    try:
        response = supabase.table("products") \
            .select("*, product_images(*), product_likes(*), product_sizes(*), product_colors(*)") \
            .eq("id", product_id) \
            .single() \
            .execute()

        if not response.data:
            return {"error": "Product not found"}

        product = response.data

        # Extract images
        images = [img["link"] for img in product.get("product_images", [])]

        # Extract sizes
        sizes = [size["size_id"] for size in product.get("product_sizes", [])]

        # Extract colors
        colors = [color["color_id"] for color in product.get("product_colors", [])]

        # Check if the product is liked
        is_liked = len(product.get("product_likes", [])) > 0

        product_data = {
            "id": product["id"],
            "category_id": product["category_id"],
            "shop_id": product["shop_id"],
            "price": product["price"],
            "description": product["description"],
            "total_ratings": product["total_ratings"],
            "materials": json.loads(product["materials"]),
            "origin": product["origin"],
            "added_date": product["added_date"],
            "is_liked": is_liked,
            "images": images,
            "sizes": sizes,
            "colors": colors,
        }

        return {"product": product_data}

    except Exception as e:
        return {"error": str(e)}


async def get_all_products():
    try:
        response = supabase.table("products").select('*, product_likes(*), product_images(*)').execute()

        products = []
        for item in response.data:
            images = item.get("product_images", [])
            image = images[0]["link"] if images else ""
            likes = item.get("product_likes", [])
            is_liked = len(likes) > 0

            products.append({
                "id": item["id"],
                "price": item["price"],
                "description": item["description"],
                "is_liked": is_liked,
                "image": image,
            })

        return {"products": products}
    except Exception as e:
        return {"error": str(e)}


async def get_products_by_context_type(context_type: str, user_id: int):
    try:
        if context_type == "history":
            response = supabase.table("product_history").select('*, products(*, product_images(*))') \
                .eq("user_id", user_id) \
                .order("visited_at", desc=True) \
                .execute()
        elif context_type == "top":
            response = supabase.table("products").select('*, product_images(*)') \
                .order("total_ratings", desc=True) \
                .limit(10) \
                .execute()
        elif context_type == "new":
            response = supabase.table("products").select('*, product_images(*)') \
                .order("added_date", desc=True) \
                .limit(10) \
                .execute()
        elif context_type == "just_for_you":
            response = supabase.table("products").select('*, product_images(*)') \
                .order("price", desc=True) \
                .limit(10) \
                .execute()
        elif context_type == "isLiked":
            response = supabase.table("product_likes").select('*, products(*, product_images(*))') \
                .eq("user_id", user_id) \
                .execute()
        else:
            return {"error": "Invalid context type"}

        products = []
        seen_product_ids = set()

        for item in response.data:
            product = item["products"] if context_type in ["history", "isLiked"] else item
            if product["id"] in seen_product_ids:
                continue 
            seen_product_ids.add(product["id"])

            images = product.get("product_images", [])
            image = images[0]["link"] if images else ""
            likes = product.get("product_likes", [])
            is_liked = len(likes) > 0

            products.append({
                "id": product["id"],
                "price": product["price"],
                "description": product["description"],
                "is_liked": is_liked,
                "image": image,
            })

        return {"products": products}
    except Exception as e:
        return {"error": str(e)}


async def search_products_by_description(keyword: str):
    try:
        response = supabase.table("products") \
            .select("*, product_images(*), product_likes(*)") \
            .ilike("description", f"*{keyword}*") \
            .limit(10) \
            .execute()


        products = []
        for product in response.data:
            images = product.get("product_images", [])
            image = images[0]["link"] if images else ""  # Extract first image

            likes = product.get("product_likes", [])
            is_liked = len(likes) > 0  # Check if the product has likes

            products.append({
                "id": product["id"],
                "price": product["price"],
                "description": product["description"],
                "is_liked": is_liked,
                "image": image,
            })

        return {"products": products}
    except Exception as e:
        return {"error": str(e)}



async def get_products_by_filters(size_id_list=None, color_id_list=None, price_range=None, category_id=None, price_order_type=None):
    try:
        query = supabase.table("products").select('*, product_images(*), product_likes(*)')

        # Filter by size IDs
        if size_id_list:
            product_ids_by_sizes_dict = supabase.table("product_sizes").select("product_id").in_("size_id", size_id_list).execute().data
            product_ids_by_sizes_list = [product_dict['product_id'] for product_dict in product_ids_by_sizes_dict]
            query = query.in_("id", product_ids_by_sizes_list)

        # Filter by color IDs
        if color_id_list:
            product_ids_by_colors_dict = supabase.table("product_colors").select("product_id").in_("color_id", color_id_list).execute().data
            product_ids_by_colors_list = [product_dict['product_id'] for product_dict in product_ids_by_colors_dict]
            query = query.in_("id", product_ids_by_colors_list)

        # Filter by price range
        if price_range:
            min_price, max_price = price_range
            query = query.gte("price", min_price).lte("price", max_price)

        # Filter by category ID
        if category_id:
            query = query.eq("category_id", category_id)

        # Order by price
        if price_order_type == "asc":
            query = query.order("price", desc=False)
        elif price_order_type == "desc":
            query = query.order("price", desc=True)

        response = query.execute()

        products = []
        for product in response.data:
            images = product.get("product_images", [])
            image = images[0]["link"] if images else ""
            likes = product.get("product_likes", [])
            is_liked = len(likes) > 0

            products.append({
                "id": product["id"],
                "price": product["price"],
                "description": product["description"],
                "is_liked": is_liked,
                "image": image,
            })

        return {"products": products}
    except Exception as e:
        return {"error": str(e)}

async def get_products_by_shop_id(shop_id: int):
    try:
        response = supabase.table("products") \
            .select("*, product_images(*), product_likes(*)") \
            .eq("shop_id", shop_id) \
            .execute()

        products = []
        for product in response.data:
            images = product.get("product_images", [])
            image = images[0]["link"] if images else ""

            likes = product.get("product_likes", [])
            is_liked = len(likes) > 0

            products.append({
                "id": product["id"],
                "price": product["price"],
                "description": product["description"],
                "total_ratings": product["total_ratings"],
                "is_liked": is_liked,
                "image": image,
            })

        return {"products": products}
    except Exception as e:
        return {"error": str(e)}


async def toggle_product_like(user_id: int, product_id: int):
    try:
        # Check if the like already exists
        response = supabase.table("product_likes") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("product_id", product_id) \
            .execute()

        if response.data:
            supabase.table("product_likes") \
                .delete() \
                .eq("user_id", user_id) \
                .eq("product_id", product_id) \
                .execute()
            return {"message": "Product unliked", "liked": False}
        else:
            supabase.table("product_likes") \
                .insert({"user_id": user_id, "product_id": product_id}) \
                .execute()
            return {"message": "Product liked", "liked": True}
    except Exception as e:
        return {"error": str(e)}

async def track_product_visit(user_id: int, product_id: int):
    try:
        supabase.table("product_history").insert({
            "user_id": user_id,
            "product_id": product_id,
        }).execute()
        return {"message": "Product visit recorded"}
    except Exception as e:
        return {"error": str(e)}

async def update_product_images(product_id: int, new_image: str):
    try:
        # Check if the product exists
        product_check = supabase.table("products").select("id").eq("id", product_id).execute()
        
        if product_check.data:
            supabase.table("product_images").delete().eq("product_id", product_id).execute()

        supabase.table("product_images").insert({
            "product_id": product_id,
            "link": new_image,
        }).execute()

        return {"message": "Product images updated successfully"}
    except Exception as e:
        return {"error": str(e)}

async def is_username_taken(username: str):
    try:
        response = supabase.table("users").select("id").eq("username", username).execute()
        return {"is_taken": len(response.data) > 0}
    except Exception as e:
        return {"error": str(e)}

async def is_shop_name_taken(shop_name: str):
    try:
        response = supabase.table("shops").select("user_id").eq("name", shop_name).execute()
        return {"is_taken": len(response.data) > 0}
    except Exception as e:
        return {"error": str(e)}

async def add_user_account(user_data: dict):
    try:
        # Check if username is taken
        username_taken = await is_username_taken(user_data.get("username"))
        if username_taken.get("is_taken"):
            return {"error": "Username is already taken"}

        # Insert the user into the `users` table
        response = supabase.table("users").insert({
            "username": user_data.get("username"),
            "email": user_data.get("email"),
            "password": user_data.get("password"),
            "language": user_data.get("language", "arabic"),
            "phone_number": user_data.get("phone_number"),
            "user_image": user_data.get("user_image"),
        }).execute()

        return {"user_id": response.data[0]["id"]}
    except Exception as e:
        return {"error": str(e)}

async def add_shop_account(shop_data: dict):
    try:
        # Add user account first
        user_response = await add_user_account({
            "username": shop_data.get("username"),
            "email": shop_data.get("email"),
            "password": shop_data.get("password"),
            "phone_number": shop_data.get("phone_number"),
            "user_image": shop_data.get("user_image"),
        })

        if "error" in user_response:
            return user_response

        user_id = user_response["user_id"]

        # Insert the shop into the `shops` table
        response = supabase.table("shops").insert({
            "user_id": user_id,
            "name": shop_data.get("shop_name"),
            "products_num": 0,
            "followers_num": 0,
            "longitude": shop_data.get("longitude"),
            "latitude": shop_data.get("latitude"),
        }).execute()

        return {"shop_id": response.data[0]["user_id"]}
    except Exception as e:
        return {"error": str(e)}

async def get_followed_shops(user_id: int):
    try:
        response = supabase.table("user_shop_follow") \
            .select("shop_id") \
            .eq("user_id", user_id) \
            .execute()

        shop_ids = [record["shop_id"] for record in response.data]

        if not shop_ids:
            return {"message": "User is not following any shops"}

        users_response = supabase.table("users") \
            .select("id, user_image") \
            .in_("id", shop_ids) \
            .execute()

        followed_shops = [
            {
                "shop_id": user["id"],
                "user_image": user["user_image"]
            }
            for user in users_response.data
        ]

        return {"followed_shops": followed_shops}
    except Exception as e:
        return {"error": str(e)}

async def get_shop_by_id(shop_id: int, user_id: int):
    try:
        # Query the shops table to get shop details
        shop_response = supabase.table("shops").select("*").eq("user_id", shop_id).execute()
        
        if not shop_response.data:
            return {"error": "Shop not found"}

        shop_data = shop_response.data[0]

        # Query the users table to get user details
        user_response = supabase.table("users").select("*").eq("id", shop_id).execute()
        
        if not user_response.data:
            return {"error": "User not found"}

        user_data = user_response.data[0]

        # Check if the user is following the shop
        follow_response = supabase.table("user_shop_follow") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("shop_id", shop_id) \
            .execute()

        is_followed = len(follow_response.data) > 0

        # Combine the data from both tables
        combined_data = {
            "shop_id": shop_data["user_id"],
            "shop_name": shop_data["name"],
            "products_num": shop_data["products_num"],
            "followers_num": shop_data["followers_num"],
            "longitude": shop_data["longitude"],
            "latitude": shop_data["latitude"],
            "username": user_data["username"],
            "email": user_data["email"],
            "phone_number": user_data["phone_number"],
            "language": user_data["language"],
            "user_image": user_data["user_image"],
            "location_id": user_data["location_id"],
            "address": user_data["address"],
            "is_followed": is_followed  # Add the is_followed field
        }

        return {"shop": combined_data}
    except Exception as e:
        return {"error": str(e)}

async def toggle_following(user_id: int, shop_id: int):
    try:
        # Check if the user is already following the shop
        follow_response = supabase.table("user_shop_follow") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("shop_id", shop_id) \
            .execute()

        if follow_response.data:
            # If the user is already following the shop, unfollow (delete the record)
            supabase.table("user_shop_follow") \
                .delete() \
                .eq("user_id", user_id) \
                .eq("shop_id", shop_id) \
                .execute()

            # Decrement the followers_num in the shops table
            supabase.table("shops") \
                .update({"followers_num": supabase.table("shops").select("followers_num").eq("user_id", shop_id).execute().data[0]["followers_num"] - 1}) \
                .eq("user_id", shop_id) \
                .execute()

            return {"message": "Unfollowed successfully"}
        else:
            supabase.table("user_shop_follow") \
                .insert({
                    "user_id": user_id,
                    "shop_id": shop_id
                }).execute()

            # Increment the followers_num in the shops table
            supabase.table("shops") \
                .update({"followers_num": supabase.table("shops").select("followers_num").eq("user_id", shop_id).execute().data[0]["followers_num"] + 1}) \
                .eq("user_id", shop_id) \
                .execute()

            return {"message": "Followed successfully"}
    except Exception as e:
        print(e)
        return {"error": str(e)}

async def update_user_image(user_id: int, new_user_image: str):
    try:
        update_response = supabase.table("users").update({
            "user_image": new_user_image
        }).eq("id", user_id).execute()

        print(update_response)

        return {"message": "User image updated successfully"}
    except Exception as e:
        print(e)
        return {"error": str(e)}

async def get_password_by_username(username: str):
    try:
        response = supabase.table("users").select("id, password").eq("username", username).execute()

        if len(response.data) == 0:
            return {"exists": False}

        return {
            "exists": True,
            "password": response.data[0]["password"]
        }
    except Exception as e:
        return {"exists": False, "error": str(e)}

async def get_all_wilayas():
    response = supabase.table("wilayas").select("id, name").execute()
    if response.data is None:
        return {"error": "Failed to fetch wilayas"}
    return {item["name"]: item["id"] for item in response.data}

async def get_wilaya_names():
    response = supabase.table("wilayas").select("name").execute()
    if response.data is None:
        return {"error": "Failed to fetch wilaya names"}
    return [item["name"] for item in response.data]

async def get_wilaya_id(name: str):
    response = supabase.table("wilayas").select("id").eq("name", name).execute()
    if response.data is None or len(response.data) == 0:
        return None
    return response.data[0]["id"]

@app.get("/")
def root():
    return {"message": "Welcome to the Wilayas API"}

@app.get("/wilayas/")
async def get_all_wilayas_endpoint():
    try:
        wilayas = await get_all_wilayas()
        if "error" in wilayas:
            raise HTTPException(status_code=400, detail=wilayas["error"])
        return {"wilayas": wilayas}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/wilayas/names/")
async def get_wilaya_names_endpoint():
    try:
        wilaya_names = await get_wilaya_names()
        if "error" in wilaya_names:
            raise HTTPException(status_code=400, detail=wilaya_names["error"])
        return {"wilaya_names": wilaya_names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/wilayas/id/")
async def get_wilaya_id_endpoint(name: str):
    try:
        wilaya_id = await get_wilaya_id(name)
        if wilaya_id is None:
            raise HTTPException(status_code=404, detail=f"No wilaya found with name '{name}'")
        return {"wilaya_id": wilaya_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Outfit Endpoints
@app.post("/outfits/")
async def add_outfit_endpoint(outfit_data: dict):
    try:
        result = await add_outfit(outfit_data)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/outfits/")
async def get_all_outfits_endpoint():
    try:
        result = await get_all_outfits()
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/outfits/context/")
async def get_outfits_by_context_type_endpoint(context_type: str, user_id: int):
    try:
        result = await get_outfits_by_context_type(context_type, user_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/outfits/search/")
async def search_outfits_by_description_endpoint(keyword: str):
    try:
        result = await search_outfits_by_description(keyword)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/outfits/filter/")
async def get_outfits_by_filters_endpoint(size_id_list: list = None, color_id_list: list = None, price_range: tuple = None, price_order_type: str = None):
    try:
        result = await get_outfits_by_filters(size_id_list, color_id_list, price_range, price_order_type)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/outfits/like/")
async def toggle_outfit_like_endpoint(user_id: int, outfit_id: int):
    try:
        result = await toggle_outfit_like(user_id, outfit_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/outfits/visit/")
async def track_outfit_visit_endpoint(user_id: int, outfit_id: int):
    try:
        result = await track_outfit_visit(user_id, outfit_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/outfits/image/")
async def update_outfit_image_endpoint(outfit_id: int, new_outfit_image: str):
    try:
        result = await update_outfit_image(outfit_id, new_outfit_image)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/outfit/")
async def get_outfit_by_id_endpoint(outfit_id: int):
    try:
        result = await get_outfit_by_id(outfit_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Product Endpoints
@app.post("/products/")
async def add_product_endpoint(product_data: dict):
    try:
        result = await add_product(product_data)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products/")
async def get_all_products_endpoint():
    try:
        result = await get_all_products()
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products/context/")
async def get_products_by_context_type_endpoint(context_type: str, user_id: int):
    try:
        result = await get_products_by_context_type(context_type, user_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products/search/")
async def search_products_by_description_endpoint(keyword: str):
    try:
        result = await search_products_by_description(keyword)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products/filter/")
async def get_products_by_filters_endpoint(size_id_list: list = None, color_id_list: list = None, price_range: tuple = None, category_id: int = None, price_order_type: str = None):
    try:
        result = await get_products_by_filters(size_id_list, color_id_list, price_range, category_id, price_order_type)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products/shop/")
async def get_products_by_shop_id_endpoint(shop_id: int):
    try:
        result = await get_products_by_shop_id(shop_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/products/like/")
async def toggle_product_like_endpoint(user_id: int, product_id: int):
    try:
        result = await toggle_product_like(user_id, product_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/products/visit/")
async def track_product_visit_endpoint(user_id: int, product_id: int):
    try:
        result = await track_product_visit(user_id, product_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/product/")
async def get_product_by_id_endpoint(product_id: int):
    try:
        result = await get_product_by_id(product_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# User Endpoints
@app.get("/users/username-taken/")
async def is_username_taken_endpoint(username: str):
    try:
        result = await is_username_taken(username)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/shop-name-taken/")
async def is_shop_name_taken_endpoint(shop_name: str):
    try:
        result = await is_shop_name_taken(shop_name)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/users/")
async def add_user_account_endpoint(user_data: dict):
    try:
        result = await add_user_account(user_data)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/shops/")
async def add_shop_account_endpoint(shop_data: dict):
    try:
        result = await add_shop_account(shop_data)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/followed-shops/")
async def get_followed_shops_endpoint(user_id: int):
    try:
        result = await get_followed_shops(user_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/shop/")
async def get_shop_by_id_endpoint(shop_id: int, user_id: int):
    try:
        result = await get_shop_by_id(shop_id, user_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/shops/toggle-following/")
async def toggle_following_endpoint(user_id: int, shop_id: int):
    try:
        result = await toggle_following(user_id, shop_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/password/")
async def get_password_endpoint(username: str):
    try:
        result = await get_password_by_username(username)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Image Endpoints
@app.post("/upload-image/")
async def upload_image_endpoint(file: UploadFile = File(...), bucket_name: str = "products"):
    try:
        result = await upload_image(file, bucket_name)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download-image/")
async def download_image_endpoint(file_name: str, bucket_name: str = "products"):
    try:
        result = await download_image(file_name, bucket_name)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        print(file_name)
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
