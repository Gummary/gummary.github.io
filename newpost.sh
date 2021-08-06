#!/bin/bash
set -e
POST_SLUG="$1"
if [ -z "$POST_SLUG" ]; then
  read -p "Post Name (e.g. your-new-post): " POST_SLUG
fi
TIMESTAMP=`date +%Y%m%d%H%M%S`
POST_FILENAME="${TIMESTAMP}-${POST_SLUG}"
hugo new "post/${POST_FILENAME}"

sed -i '' "s/title: \"Index\"/title: \"$POST_SLUG\"/g" content/post/${POST_FILENAME}/index.md
sed -i '' "s/slug: index/slug: $POST_SLUG/g" content/post/${POST_FILENAME}/index.md