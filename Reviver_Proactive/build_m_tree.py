import os
from dotenv import load_dotenv
from pre_processor import Photo_PreProcessor


if __name__ == "__main__":
    load_dotenv()
    api_key=os.getenv("GPT_API_KEY")
    user = "wl_2"
    
    
    ### Generate photo descriptions
    Processor = Photo_PreProcessor(api_key, user, has_meta_data=False)
    Processor.batch_photo_extraction(1, 19)
    Processor.save_m_tree()
    
    
    ### Slice photos and build m_tree
    # Processor = Photo_PreProcessor(api_key, user, has_meta_data=False, old_mtree_file="memory_tree.json")
    # slice_locs = [1, 3, 7, 11, 14, 18, 21]
    # Processor.build_m_tree(slice_locs)
    
    

    # Processor.single_photo_exact_location(51)
    # Processor.batch_photo_extraction(2, 1)
    # Processor.save_m_tree()

    # Processor.slice()

    # Processor = Photo_PreProcessor(api_key, "xj_1", has_meta_data=False, old_mtree_file="memory_tree.json")
    # slice_locs = [1,3,5,9,11,14,20,27,35]
    # Processor.build_m_tree(slice_locs)