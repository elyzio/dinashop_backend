from .customer import (
    CustomerDeactivateView, CustomerDetailView, CustomerListCreateView,
    CustomerReactivateView,
)
from .helper import (
    HelperDeactivateView, HelperDetailView, HelperListCreateView,
    HelperReactivateView,
)

__all__ = [name for name in globals() if name.endswith("View")]
