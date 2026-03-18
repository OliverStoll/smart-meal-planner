import pandas as pd

SUPERMARKET_FRIENDLY_NAMES = {
    "Netto Marken-Discount": "Netto",
    "Kaufland": "Kaufland",
    "EDEKA": "Edeka",
    "Lidl": "Lidl",
    "Aldi Nord": "Aldi",
    "Rewe": "Rewe",
}


def clean_sellers(
    data_path: str = "data/supermarkets/product_data.csv",
) -> pd.DataFrame:
    data = pd.read_csv(data_path)
    data["sellers"] = data["sellers"].str.split("ist bei ", expand=True)[1]
    data["sellers"] = data["sellers"].str.split(" erhältlich", expand=True)[0]
    data["sellers"] = data["sellers"].str.replace(" und ", ", ")
    data["sellers"] = data["sellers"].fillna("").str.split(", ")
    data["sellers"] = data["sellers"].apply(lambda x: [seller.strip() for seller in x])
    data["sellers_partially"] = data["sellers"].apply(
        lambda x: [seller.split(" (gelegentlich")[0] for seller in x if "(gelegentlich im Sortiment)" in seller]
    )
    data["sellers_always"] = data["sellers"].apply(
        lambda x: [seller for seller in x if "(gelegentlich im Sortiment)" not in seller]
    )
    data["sellers_always"] = data["sellers"].apply(
        lambda x: [
            SUPERMARKET_FRIENDLY_NAMES.get(seller, seller) for seller in x if seller in SUPERMARKET_FRIENDLY_NAMES
        ]
    )
    data["sellers_always"] = data["sellers_always"].apply(lambda x: ", ".join(x))
    return data


if __name__ == "__main__":
    data = clean_sellers()
    lidl_data = data[data["sellers_always"].str.contains("Lidl")]
    lidl_data_titles = lidl_data[["title"]]
    print(data.head())
