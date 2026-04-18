def calculate_dsi(detections, image_shape):
    """
    DSI (Damage Severity Index) calculate karne ka logic.

    Arguments:
    - detections: List of dicts (AI se mili hui list jisme 'box' coordinates hain)
    - image_shape: Original image ki dimensions (height, width, channels)

    Returns:
    - float: 0 se 100 ke beech ka severity score.
    """

    # 1. Agar koi detection nahi hai, toh damage zero hai
    if not detections or detections is None:
        return 0.0

    try:
        # 2. Image ka total area nikalna (pixels mein)
        img_h, img_w = image_shape[:2]
        total_img_area = img_h * img_w

        total_damage_area = 0

        # 3. Har detect kiye gaye dent/scratch ka area calculate karna
        for det in detections:
            # Box format: [x1, y1, x2, y2]
            box = det.get("box", [0, 0, 0, 0])

            # Width = x2 - x1 | Height = y2 - y1
            width = max(0, box[2] - box[0])
            height = max(0, box[3] - box[1])

            area = width * height
            total_damage_area += area

        # 4. Severity Ratio (%) nikalna
        # Formula: (Damage Area / Total Car Image Area) * 100
        severity_ratio = (total_damage_area / total_img_area) * 100

        # 5. DSI Scaling Logic:
        # Car damage aksar puri car ke mukable chota hota hai,
        # isliye hum factor (jaise 10) use karte hain score ko meaningful banane ke liye.
        # Agar damage area 5% hai, toh DSI score 50 ho jayega.
        dsi_score = severity_ratio * 10

        # 6. Score ko 100 ki limit mein rakhna
        final_score = min(100.0, dsi_score)

        return round(float(final_score), 2)

    except Exception as e:
        print(f"Error in DSI calculation: {e}")
        return 0.0
