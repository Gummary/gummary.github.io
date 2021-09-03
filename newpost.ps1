if ($args.Count -eq 0) {
    Write-Host "Please input blog name."
    exit
}

$POST_SLUG=$args[0]
$TIMESTAMP=Get-Date -Format "yyyyMMddHHmmss"
$POST_NAME="${TIMESTAMP}-${POST_SLUG}"


hugo new "post/$POST_NAME"

(Get-Content content/post/$POST_NAME/index.md).replace('"Index"', """$POST_SLUG""") | Set-Content content/post/$POST_NAME/index.md
(Get-Content content/post/$POST_NAME/index.md).replace('slug: index', "slug: ""$POST_SLUG""") | Set-Content content/post/$POST_NAME/index.md
