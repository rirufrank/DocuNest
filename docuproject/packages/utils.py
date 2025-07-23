def get_company_limits(user):
    if hasattr(user, 'userpackage') and user.user_type == 'company':
        package = user.userpackage.package
        return {
            'max_employees': package.max_employees,
            'max_departments': package.max_departments
        }
    return {'max_employees': 0, 'max_departments': 0}
