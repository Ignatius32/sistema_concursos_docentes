# Tribunal Portal Style Guide

## Overview
This guide documents the unified styling system used in the Tribunal Portal to ensure consistency across all components. The design uses a modern, professional color scheme based on blues, greys, and teal accents.

## Color Palette

### Primary Colors
- **Primary Blue**: `#2563eb` - Main action color, primary buttons, active states
- **Secondary Blue**: `#3b82f6` - Light blue variant for headers and highlights  
- **Accent Teal**: `#0891b2` - Secondary action color, accent elements
- **Success Green**: `#059669` - Success states, positive actions
- **Warning Orange**: `#d97706` - Warning states, attention needed
- **Grey Medium**: `#6b7280` - Secondary actions, muted elements
- **Grey Light**: `#f3f4f6` - Background, subtle borders

### State Colors
- **Info**: `#0891b2` (same as accent teal)
- **Success**: `#059669` 
- **Warning**: `#d97706`
- **Danger/Error**: `#dc2626` (standard red)

## Typography

### Headers
```css
/* Card headers with primary styling */
.header-primary { 
    background-color: #2563eb; 
    color: white; 
    font-weight: 600;
}

/* Alternative header styles */
.header-blue-light { background-color: #3b82f6; color: white; }
.header-grey-medium { background-color: #6b7280; color: white; }
.header-grey-light { background-color: #f3f4f6; color: #374151; border-bottom: 1px solid #d1d5db; }
.header-orange { background-color: #0891b2; color: white; }
```

### Text Hierarchy
- **Card titles**: `h4` with `font-size: 1.1rem`, `font-weight: 600`
- **Section labels**: `h6` with `color: #2563eb`, `font-weight: 600`
- **Body text**: Standard with `line-height: 1.4`
- **Strong labels**: `color: #374151`, `font-weight: 600`, `min-width: 120px`

## Button System

### Button Variants
```html
<!-- Primary Actions -->
<button class="btn btn-tribunal-primary">
    <i class="bi bi-icon"></i> Primary Action
</button>

<!-- Secondary Actions -->
<button class="btn btn-tribunal-secondary">
    <i class="bi bi-icon"></i> Secondary Action
</button>

<!-- Accent Actions -->
<button class="btn btn-tribunal-accent">
    <i class="bi bi-icon"></i> Accent Action
</button>

<!-- Success Actions -->
<button class="btn btn-tribunal-success">
    <i class="bi bi-icon"></i> Success Action
</button>
```

### Button Sizes
- **Small**: `btn-sm` - `padding: 0.375rem 0.75rem`, `font-size: 0.875rem`
- **Regular**: Default Bootstrap size
- **Large**: `btn-lg` - Enhanced with shadow and transform effects
- **Extra Small**: `btn-xs` - `padding: 0.25rem 0.5rem`, `font-size: 0.75rem`

### Button States
All tribunal buttons include:
- Hover effects with darker shades
- Focus states with colored shadows
- Icon spacing with `margin-right: 0.25rem` for small buttons

## Badge System

### Badge Usage
Badges use maximum specificity to override Bootstrap defaults:

```html
<!-- Role/Status Badges -->
<span class="badge badge-tribunal-primary">PRESIDENTE</span>
<span class="badge badge-tribunal-secondary">VOCAL</span>
<span class="badge badge-tribunal-accent">SUPLENTE</span>

<!-- State Badges -->
<span class="badge badge-tribunal-success">FIRMADO</span>
<span class="badge badge-tribunal-warning">PENDIENTE</span>
<span class="badge badge-tribunal-info">EN_PROCESO</span>
```

### Badge Colors
- **Primary**: `#2563eb` with white text
- **Secondary**: `#6b7280` with white text  
- **Accent**: `#f97316` (orange variant) with white text
- **Success**: `#059669` with white text
- **Warning**: `#d97706` with white text
- **Info**: `#0891b2` with white text

## Tab System

### Tab Structure
```html
<ul class="nav nav-tabs tribunal-tabs mb-4" id="tabsId" role="tablist">
    <li class="nav-item" role="presentation">
        <button class="nav-link active" id="tab1-tab" data-bs-toggle="tab" 
                data-bs-target="#tab1" type="button" role="tab">
            <i class="bi bi-icon"></i> Tab Name
        </button>
    </li>
</ul>

<div class="tab-content tribunal-tab-content" id="tabsContent">
    <div class="tab-pane fade show active" id="tab1" role="tabpanel">
        <div class="card">
            <div class="card-header header-primary">
                <h4 class="mb-0"><i class="bi bi-icon"></i> Section Title</h4>
            </div>
            <div class="card-body">
                <!-- Content -->
            </div>
        </div>
    </div>
</div>
```

### Tab Styling Features
- **Rounded top corners**: `border-radius: 0.5rem 0.5rem 0 0`
- **Smooth transitions**: `transition: all 0.3s ease`
- **Active state**: Blue border and background
- **Hover effects**: Light background with blue text
- **Icon spacing**: `margin-right: 0.5rem`
- **Content border**: Unified border around tab content area

### Tab Content Cards
- **No border/shadow** on cards within tabs (handled by tab container)
- **Header styling** with `.header-primary` class
- **Consistent padding**: `1.5rem` in card body
- **Border styling**: `1px solid #e5e7eb` on card body

## Table System

### Table Classes
```html
<div class="table-responsive tribunal-table">
    <table class="table table-striped table-hover">
        <thead class="table-light">
            <tr>
                <th>Column Header</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Data</td>
            </tr>
        </tbody>
    </table>
</div>
```

### Table Styling
- **Header background**: `#f1f5f9` with `#374151` text
- **Stripe color**: `#f8fafc` for odd rows
- **Hover color**: `#e2e8f0`
- **Border color**: `#e2e8f0` throughout
- **Vertical alignment**: `middle` for all cells

## Card System

### Standard Card Structure
```html
<div class="card tribunal-card">
    <div class="card-header header-primary">
        <h4 class="mb-0"><i class="bi bi-icon"></i> Card Title</h4>
    </div>
    <div class="card-body">
        <!-- Content with proper spacing -->
        <p><strong>Label:</strong> Value</p>
    </div>
</div>
```

### Card Features
- **Shadow**: `0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)`
- **Border**: `1px solid #e5e7eb`
- **Header border**: `1px solid #d1d5db` bottom border
- **Enhanced cards**: Use `.tribunal-card` class for additional styling

## List Groups

### List Group Structure
```html
<div class="list-group">
    <div class="list-group-item">
        <div class="d-flex w-100 justify-content-between align-items-center">
            <div>
                <h5 class="mb-1">Item Title</h5>
                <span class="badge badge-tribunal-primary">Badge</span>
            </div>
        </div>
    </div>
</div>
```

### List Group Features
- **Padding**: `1rem` for comfortable spacing
- **Hover effect**: Light background `#f8fafc`
- **Title styling**: `color: #374151`, `font-weight: 600`
- **Badge spacing**: `margin-top: 0.25rem`, `margin-left: 0.5rem` between badges

## Alert System

### Alert Classes
```html
<div class="alert alert-tribunal-info">Info message</div>
<div class="alert alert-tribunal-warning">Warning message</div>
<div class="alert alert-tribunal-success">Success message</div>
```

### Alert Colors
- **Info**: `#eff6ff` background, `#bfdbfe` border, `#1e40af` text
- **Warning**: `#f0f9ff` background, `#cff7fe` border, `#0e7490` text
- **Success**: `#f0fdf4` background, `#bbf7d0` border, `#15803d` text

## Special Features

### Notification Badges
```html
<span class="badge bg-danger ms-2 notification-badge">3</span>
```
- **Size**: `font-size: 0.75rem`, `padding: 0.25rem 0.5rem`
- **Used on**: Tab headers to indicate pending items

### Breadcrumb Navigation
```html
<nav aria-label="breadcrumb" class="mb-3 tribunal-breadcrumb">
    <ol class="breadcrumb mb-0">
        <li class="breadcrumb-item">
            <a href="#"><i class="bi bi-house"></i> Home</a>
        </li>
        <li class="breadcrumb-item active">Current Page</li>
    </ol>
</nav>
```

### Instructivo Sections
```html
<div class="mb-3">
    <h6><i class="bi bi-check2-circle"></i> Section Title</h6>
    <p class="text-muted">Content with special background and border</p>
</div>
```
- **Background**: `#f8fafc`
- **Padding**: `1rem`
- **Border**: `4px solid #3b82f6` on left
- **Border radius**: `6px`

## Responsive Design

### Mobile Adaptations (max-width: 768px)
- **Tab links**: Smaller font size (`0.875rem`) and padding
- **Tab content**: Reduced padding (`1rem`)
- **Icon spacing**: Reduced to `0.25rem`

### Best Practices
1. **Always use icon + text** in buttons and tabs
2. **Maintain consistent spacing** with defined padding/margins
3. **Use semantic colors** (success for positive actions, warning for attention)
4. **Include hover and focus states** for interactive elements
5. **Ensure accessibility** with proper ARIA labels and color contrast
6. **Test responsive behavior** on different screen sizes

## Implementation Notes

### CSS Loading
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/tribunal.css') }}?v=2.0">
```

### JavaScript Features
- **Tab persistence**: Active tab saved to localStorage
- **Notification badges**: Dynamic badge updates based on content
- **Form loading states**: Disable buttons during form submission

### Required Dependencies
- **Bootstrap 5.x**: Core framework
- **Bootstrap Icons**: Icon system
- **Custom tribunal.css**: Extended styling system

This style guide ensures consistent, professional appearance across all tribunal portal interfaces while maintaining accessibility and responsive design principles.
