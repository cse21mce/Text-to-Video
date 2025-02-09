def generate_video(_id,images,translations):
    """
    Generate video from images and translations.
    
    Args:
        images (list): The images to be used in the video
        translations (dict): The translated text to be used in the video
        
    Returns:
        None
    """
    print(images,translations)
    
    return None


# ['https://static.pib.gov.in/WriteReadData/specificdocs/photo/2021/aug/ph202183101.png', 'https://static.pib.gov.in/WriteReadData/userfiles/image/image001M9KV.jpg', 'https://static.pib.gov.in/WriteReadData/userfiles/image/image002J0GD.jpg', 'https://static.pib.gov.in/WriteReadData/userfiles/image/image003RDY0.jpg', 'https://upload.wikimedia.org/wikipedia/commons/8/85/The_Union_Minister_for_Petroleum_%26_Natural_Gas%2C_Shri_Dharmendra_Pradhan_being_greeted_by_the_Secretary%2C_Ministry_of_Petroleum_%26_Natural_Gas%2C_Dr._M.M._Kutty%2C_in_New_Delhi_on_May_31%2C_2019_%28cropped%29.jpg', 'https://www.thestatesman.com/wp-content/uploads/2025/02/Untitled-design-2025-02-08T170453.425-jpg.webp', 'https://www.nbtindia.gov.in/ndwbf2025/assetsndwbf2025/images/web_banner_for_2025.jpg'] 

# [{'audio': '\\output\\Shri_Dharmendra_Pradhan_launches_41_books_under_PM_YUVA_20_at_NDWBF_2025\\hindi.mp3', 'text': '\\output\\Shri_Dharmendra_Pradhan_launches_41_books_under_PM_YUVA_20_at_NDWBF_2025\\hindi.srt'}, {'audio': '\\output\\Shri_Dharmendra_Pradhan_launches_41_books_under_PM_YUVA_20_at_NDWBF_2025\\urdu.mp3', 'text': '\\output\\Shri_Dharmendra_Pradhan_launches_41_books_under_PM_YUVA_20_at_NDWBF_2025\\urdu.srt'}, {'audio': '\\output\\Shri_Dharmendra_Pradhan_launches_41_books_under_PM_YUVA_20_at_NDWBF_2025\\gujrati.mp3', 'text': '\\output\\Shri_Dharmendra_Pradhan_launches_41_books_under_PM_YUVA_20_at_NDWBF_2025\\gujrati.srt'}, {'audio': '\\output\\Shri_Dharmendra_Pradhan_launches_41_books_under_PM_YUVA_20_at_NDWBF_2025\\marathi.mp3', 'text': '\\output\\Shri_Dharmendra_Pradhan_launches_41_books_under_PM_YUVA_20_at_NDWBF_2025\\marathi.srt'}, {'audio': '\\output\\Shri_Dharmendra_Pradhan_launches_41_books_under_PM_YUVA_20_at_NDWBF_2025\\telugu.mp3', 'text': '\\output\\Shri_Dharmendra_Pradhan_launches_41_books_under_PM_YUVA_20_at_NDWBF_2025\\telugu.srt'}, {'audio': '\\output\\Shri_Dharmendra_Pradhan_launches_41_books_under_PM_YUVA_20_at_NDWBF_2025\\kannada.mp3', 'text': '\\output\\Shri_Dharmendra_Pradhan_launches_41_books_under_PM_YUVA_20_at_NDWBF_2025\\kannada.srt'}, {'audio': '\\output\\Shri_Dharmendra_Pradhan_launches_41_books_under_PM_YUVA_20_at_NDWBF_2025\\malayalam.mp3', 'text': '\\output\\Shri_Dharmendra_Pradhan_launches_41_books_under_PM_YUVA_20_at_NDWBF_2025\\malayalam.srt'}, {'audio': '\\output\\Shri_Dharmendra_Pradhan_launches_41_books_under_PM_YUVA_20_at_NDWBF_2025\\tamil.mp3', 'text': '\\output\\Shri_Dharmendra_Pradhan_launches_41_books_under_PM_YUVA_20_at_NDWBF_2025\\tamil.srt'}, {'audio': '\\output\\Shri_Dharmendra_Pradhan_launches_41_books_under_PM_YUVA_20_at_NDWBF_2025\\bengali.mp3', 'text': '\\output\\Shri_Dharmendra_Pradhan_launches_41_books_under_PM_YUVA_20_at_NDWBF_2025\\bengali.srt'}]