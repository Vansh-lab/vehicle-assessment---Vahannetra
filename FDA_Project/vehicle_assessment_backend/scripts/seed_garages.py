from app.services.bootstrap import init_seed_data


if __name__ == "__main__":
    init_seed_data()
    print("Seed complete: garages + insurance centers initialized")
