from django import template
register = template.Library()

@register.filter
def primary_parent(student):
    sp = student.studentparent_set.filter(is_primary_contact=True).first()
    if not sp: sp = student.studentparent_set.first()
    return sp.parent.full_name if sp else '-'

@register.filter
def primary_address(student):
    sp = student.studentparent_set.filter(is_primary_contact=True).first()
    if not sp: sp = student.studentparent_set.first()
    return sp.parent.address if sp else '-'


@register.filter
def get_item(dictionary, key):
    if not dictionary:
        return None
    return dictionary.get(key)


@register.filter
def dict_get(dictionary, key):
    return get_item(dictionary, key)



