import os
from dotenv import load_dotenv
from pre_processor import Photo_PreProcessor


if __name__ == "__main__":
    load_dotenv()
    api_key=os.getenv("OPENAI_API_KEY")
    Processor = Photo_PreProcessor(api_key, "hjs_2", has_meta_data=False, old_mtree_file="memory_tree.json")

    # Processor.single_photo_exact_location(51)
    # Processor.batch_photo_extraction(26, 8)
    # Processor.save_m_tree()

    # Processor.slice()

    slice_locs = [1,9,14,18,24,26,28,34]
    Processor.build_m_tree(slice_locs)