# Tribunal Portal Style Guide

## Color Palette

### Primary Colors
- **Primary Blue**: `#2563eb` (Bootstrap's blue-600) - Main headers and primary actions
- **Light Blue**: `#3b82f6` (Bootstrap's blue-500) - Secondary headers and information sections
- **Dark Blue**: `#1e40af` (Bootstrap's blue-700) - Active states and emphasis

### Secondary Colors
- **Medium Grey**: `#6b7280` (Bootstrap's gray-500) - General information and neutral sections
- **Light Grey**: `#f3f4f6` (Bootstrap's gray-100) - Background sections and subtle headers
- **Dark Grey**: `#374151` (Bootstrap's gray-700) - Text on light backgrounds

### Accent Colors
- **Orange**: `#f97316` (Bootstrap's orange-500) - Highlights, warnings, and important actions
- **Light Orange**: `#fed7aa` (Bootstrap's orange-200) - Subtle highlights and backgrounds

## CSS File Location

All tribunal styles are now centralized in:
**`app/static/css/tribunal.css`**

To use these styles in any template, include:
```html
{% block styles %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/tribunal.css') }}">
{% endblock %}
```

## Section Color Mapping

### Portal Concurso Headers
1. **General** (Información del Concurso): Primary Blue (`bg-primary`) - Most important section
2. **Sustanciación**: Light Blue (`bg-blue-500`) - Process information
3. **Documentos**: Medium Grey (`bg-gray-600`) - Document management
4. **Tribunal & Postulantes**: 
   - Tribunal: Medium Grey (`bg-gray-600`) - Administrative info
   - Postulantes: Orange (`bg-orange-500`) - Highlighted information
5. **Temas de Sorteo**: Orange (`bg-orange-500`) - Important action required
6. **Asignaturas**: Light Grey (`bg-gray-100`) - External/reference information

### Portal Principal Headers
- **Información Personal**: Light Grey (`bg-gray-100`) - Basic user info
- **Concursos Table**: Standard Bootstrap table styling with blue accents

## CSS Classes Available

### Header Classes:
- `.header-primary` - Primary Blue (#2563eb) with white text
- `.header-blue-light` - Light Blue (#3b82f6) with white text
- `.header-grey-medium` - Medium Grey (#6b7280) with white text
- `.header-grey-light` - Light Grey (#f3f4f6) with dark text
- `.header-orange` - Orange (#f97316) with white text
- `.header-orange-light` - Light Orange (#fed7aa) with dark text

### Button Classes:
- `.btn-tribunal-primary` - Primary blue buttons with hover and focus effects
- `.btn-tribunal-secondary` - Grey buttons with hover and focus effects
- `.btn-tribunal-accent` - Orange accent buttons with hover and focus effects

### Badge Classes:
- `.badge-tribunal-primary` - Primary blue badges
- `.badge-tribunal-secondary` - Grey badges  
- `.badge-tribunal-accent` - Orange badges
- `.badge-tribunal-success` - Green badges (for completed/successful states)
- `.badge-tribunal-warning` - Amber badges (for in-progress/warning states)
- `.badge-tribunal-info` - Cyan badges (for informational states)

### Layout Classes:
- `.tribunal-tabs` - Apply to nav-tabs for tribunal-specific tab styling
- `.tribunal-tab-content` - Apply to tab-content for tribunal-specific content styling
- `.tribunal-table` - Apply to table containers for enhanced table styling
- `.tribunal-card` - Apply to cards for enhanced card styling

### Alert Classes:
- `.alert-tribunal-info` - Blue-themed info alerts
- `.alert-tribunal-warning` - Orange-themed warning alerts
- `.alert-tribunal-success` - Green-themed success alerts

### Utility Classes:
- `.temas-list` - Flex layout for tema badges
- `.notification-badge` - Small notification badges for tabs

## Usage Guidelines

1. **Primary Blue**: Use for the most important sections and primary actions
2. **Light Blue**: Use for secondary important information
3. **Medium Grey**: Use for administrative or neutral information
4. **Light Grey**: Use for background information or less critical sections
5. **Orange**: Use for highlights, warnings, or sections requiring user attention
6. **Light Orange**: Use for subtle highlights or secondary accent areas

## Consistency Rules

1. Always use white text on dark backgrounds (Primary Blue, Light Blue, Medium Grey, Orange)
2. Use dark grey text on light backgrounds (Light Grey, Light Orange)
3. Maintain consistent spacing and border radius across all sections
4. Use the same icon style (Bootstrap Icons) throughout
5. Keep hover states consistent with the base color palette

## Bootstrap Class Equivalents

For easy implementation with Bootstrap:
- `bg-primary` → Primary Blue
- `bg-blue-500` → Light Blue (custom class needed)
- `bg-gray-600` → Medium Grey (custom class needed)
- `bg-gray-100` → Light Grey (custom class needed)
- `bg-orange-500` → Orange (custom class needed)
- `bg-orange-200` → Light Orange (custom class needed)

## Future Considerations

- Consider adding dark mode variants
- Maintain accessibility standards (WCAG 2.1 AA)
- Test color combinations for color-blind users
- Keep print-friendly alternatives in mind
