"""Shared API infrastructure for all domain applications.

Keep this package initializer import-free because DRF imports permission classes
while its own view module is still being initialized.
"""
