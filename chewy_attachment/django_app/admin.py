"""Django admin configuration for ChewyAttachment"""

from django import forms
from django.contrib import admin
from django.utils.safestring import mark_safe

from ..core.storage import FileStorageEngine
from ..core.utils import generate_uuid
from .models import Attachment, get_storage_root


def format_file_size(size_bytes):
    """Format file size to human readable format"""
    if size_bytes is None:
        return "-"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


class AttachmentAddForm(forms.ModelForm):
    """新建附件表单 - 只需上传文件、设置权限"""

    file = forms.FileField(label="上传文件", required=True)

    class Meta:
        model = Attachment
        fields = ["file", "owner_id", "is_public"]

    def save(self, commit=True):
        instance = super().save(commit=False)

        # 处理文件上传
        uploaded_file = self.cleaned_data.get("file")
        if uploaded_file:
            content = uploaded_file.read()
            original_name = uploaded_file.name

            storage = FileStorageEngine(get_storage_root())
            result = storage.save_file(content, original_name)

            instance.id = generate_uuid()
            instance.original_name = original_name
            instance.storage_path = result.storage_path
            instance.mime_type = result.mime_type
            instance.size = result.size

        if commit:
            instance.save()
        return instance


class AttachmentChangeForm(forms.ModelForm):
    """编辑附件表单 - 只能修改权限设置"""

    class Meta:
        model = Attachment
        fields = ["owner_id", "is_public"]


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    """Admin configuration for Attachment model"""

    # 使用不同的表单用于新建和编辑
    add_form = AttachmentAddForm
    form = AttachmentChangeForm

    # List view configuration
    list_display = [
        "file_preview",
        "original_name",
        "file_type_badge",
        "formatted_size",
        "owner_id",
        "visibility_badge",
        "created_at",
    ]
    list_display_links = ["original_name"]
    list_filter = [
        "is_public",
        "mime_type",
        ("created_at", admin.DateFieldListFilter),
    ]
    search_fields = ["original_name", "owner_id", "id"]
    ordering = ["-created_at"]
    list_per_page = 25
    date_hierarchy = "created_at"

    # 新建表单 - 简化输入
    add_fieldsets = (
        (
            "上传文件",
            {
                "fields": ("file",),
                "description": "选择要上传的文件",
            },
        ),
        (
            "权限设置",
            {
                "fields": ("owner_id", "is_public"),
            },
        ),
    )

    # 编辑/查看表单
    fieldsets = (
        (
            "文件信息",
            {
                "fields": (
                    "id",
                    "original_name",
                    "file_preview_large",
                    "formatted_size_display",
                ),
            },
        ),
        (
            "权限设置",
            {
                "fields": ("owner_id", "is_public"),
            },
        ),
        (
            "存储详情",
            {
                "fields": ("storage_path", "mime_type", "created_at"),
                "classes": ("collapse",),
            },
        ),
    )

    # Actions
    actions = ["make_public", "make_private"]

    def get_form(self, request, obj=None, **kwargs):
        """新建时使用 add_form，编辑时使用 form"""
        if obj is None:
            return self.add_form
        return super().get_form(request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        """新建时使用简化的 fieldsets"""
        if obj is None:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def get_readonly_fields(self, request, obj=None):
        """编辑时大部分字段只读"""
        if obj is None:
            return []
        return [
            "id",
            "original_name",
            "file_preview_large",
            "storage_path",
            "mime_type",
            "formatted_size_display",
            "created_at",
        ]

    @admin.display(description="预览")
    def file_preview(self, obj):
        """Show thumbnail preview for images"""
        if obj.mime_type and obj.mime_type.startswith("image/"):
            return mark_safe(
                f'<img src="/api/attachments/files/{obj.id}/preview/" '
                f'style="max-width: 50px; max-height: 50px; object-fit: cover; '
                f'border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.2);" '
                f'onerror="this.outerHTML=&quot;<span style=&apos;color: red; font-size: 12px;&apos;>❌ 加载失败</span>&quot;" />'
            )
        # Non-image files: show type info
        return mark_safe(f'<span style="color: #999; font-size: 12px;">{obj.mime_type or "未知"}</span>')

    @admin.display(description="文件预览")
    def file_preview_large(self, obj):
        """Show larger preview in detail view"""
        if obj.mime_type and obj.mime_type.startswith("image/"):
            mime_escaped = obj.mime_type.replace('"', '&quot;')
            return mark_safe(
                f'<div style="text-align: center;">'
                f'<img src="/api/attachments/files/{obj.id}/preview/" '
                f'style="max-width: 400px; max-height: 400px; object-fit: contain; '
                f'border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);" '
                f'onerror="this.outerHTML=&quot;<div style=&apos;color: red; padding: 40px; font-size: 16px;&apos;>❌ 图片加载失败<br/><small style=&apos;color: #999;&apos;>{mime_escaped}</small></div>&quot;" />'
                f'</div>'
            )
        # Non-image files: show type info
        return mark_safe(
            f'<div style="text-align: center; padding: 40px; color: #999;">'
            f'<p style="font-size: 16px; margin: 0;">非图片文件</p>'
            f'<p style="font-size: 14px; margin-top: 8px;">{obj.mime_type or "未知类型"}</p>'
            f'</div>'
        )

    @admin.display(description="文件类型")
    def file_type_badge(self, obj):
        """Show file type as a colored badge"""
        mime = obj.mime_type or "unknown"
        color = self._get_type_color(mime)
        type_name = mime.split("/")[-1].upper()[:10]
        return mark_safe(
            f'<span style="background-color: {color}; color: white; padding: 2px 8px; '
            f'border-radius: 12px; font-size: 11px; font-weight: 500;">{type_name}</span>'
        )

    @admin.display(description="文件大小", ordering="size")
    def formatted_size(self, obj):
        """Display formatted file size"""
        return format_file_size(obj.size)

    @admin.display(description="文件大小")
    def formatted_size_display(self, obj):
        """Display formatted file size in detail view"""
        if obj.size is None:
            return "-"
        return f"{format_file_size(obj.size)} ({obj.size:,} 字节)"

    @admin.display(description="可见性")
    def visibility_badge(self, obj):
        """Show visibility as a colored badge"""
        if obj.is_public:
            return mark_safe(
                '<span style="background-color: #28a745; color: white; '
                'padding: 2px 8px; border-radius: 12px; font-size: 11px;">🌐 公开</span>'
            )
        return mark_safe(
            '<span style="background-color: #6c757d; color: white; '
            'padding: 2px 8px; border-radius: 12px; font-size: 11px;">🔒 私有</span>'
        )

    @admin.action(description="✅ 设为公开")
    def make_public(self, request, queryset):
        """Bulk action to make files public"""
        updated = queryset.update(is_public=True)
        self.message_user(request, f"已将 {updated} 个文件设为公开")

    @admin.action(description="🔒 设为私有")
    def make_private(self, request, queryset):
        """Bulk action to make files private"""
        updated = queryset.update(is_public=False)
        self.message_user(request, f"已将 {updated} 个文件设为私有")

    def _get_file_icon(self, mime_type):
        """Get emoji icon based on mime type"""
        if not mime_type:
            return "📄"
        if mime_type.startswith("image/"):
            return "🖼️"
        if mime_type.startswith("video/"):
            return "🎥"
        if mime_type.startswith("audio/"):
            return "🎧"
        if mime_type.startswith("text/"):
            return "📝"
        if "pdf" in mime_type:
            return "📁"
        if "zip" in mime_type or "rar" in mime_type or "tar" in mime_type:
            return "📦"
        if "word" in mime_type or "document" in mime_type:
            return "📘"
        if "excel" in mime_type or "spreadsheet" in mime_type:
            return "📊"
        if "powerpoint" in mime_type or "presentation" in mime_type:
            return "📽️"
        return "📄"

    def _get_type_color(self, mime_type):
        """Get color based on mime type"""
        if not mime_type:
            return "#6c757d"
        if mime_type.startswith("image/"):
            return "#17a2b8"
        if mime_type.startswith("video/"):
            return "#dc3545"
        if mime_type.startswith("audio/"):
            return "#fd7e14"
        if mime_type.startswith("text/"):
            return "#28a745"
        if "pdf" in mime_type:
            return "#dc3545"
        if "zip" in mime_type or "rar" in mime_type:
            return "#ffc107"
        if "word" in mime_type or "document" in mime_type:
            return "#2b579a"
        if "excel" in mime_type or "spreadsheet" in mime_type:
            return "#217346"
        return "#6c757d"
