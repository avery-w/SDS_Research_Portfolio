from math import ceil
from catalog.models import Product

def billable_weight_lb(w_lb, l_in, w_in, h_in):
    dim = ceil((float(l_in) * float(w_in) * float(h_in)) / 139.0)
    return int(ceil(max(float(w_lb or 0), float(dim))))

def build_packages_from_items(items):
    # items: [{"product_id":..., "quantity":...}]
    packages = []
    defaults = {"weight_lb": 1, "length_in": 8, "width_in": 6, "height_in": 2}
    products = {p.id: p for p in Product.objects.filter(id__in=[i.get("product_id") for i in items], is_active=True)}
    for it in items:
        pid = it.get("product_id")
        qty = int(it.get("quantity", 1))
        qty = max(1, min(qty, 50))
        p = products.get(pid)
        if not p:
            continue
        w = float(p.weight_lb or defaults["weight_lb"])
        L = float(p.length_in or defaults["length_in"])
        W = float(p.width_in or defaults["width_in"])
        H = float(p.height_in or defaults["height_in"])
        weight = billable_weight_lb(w, L, W, H)
        for _ in range(qty):
            packages.append({"weight_lb": weight, "length_in": L, "width_in": W, "height_in": H})
    return packages
