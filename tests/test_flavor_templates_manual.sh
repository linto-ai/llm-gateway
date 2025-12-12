#!/bin/bash

# Flavor Templates - Manual API Tests
# Run these tests against the running backend to verify bug fixes

BASE_URL="http://localhost:8000"
PASSED=0
FAILED=0

# Get existing data
PROVIDER_ID=$(curl -s "${BASE_URL}/api/v1/providers?limit=1" | jq -r '.items[0].id')
MODEL_ID=$(curl -s "${BASE_URL}/api/v1/models?limit=1" | jq -r '.items[0].id')
SERVICE_ID=$(curl -s "${BASE_URL}/api/v1/services?limit=1" | jq -r '.items[0].id')

# Create test prompt templates
echo "Creating test templates..."
SYSTEM_TEMPLATE_ID=$(curl -s -X POST "${BASE_URL}/api/v1/prompts" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "flavor-test-system-template",
    "content": "You are a helpful assistant that summarizes conversations.",
    "language": "en",
    "is_template": true,
    "template_category": "system"
  }' | jq -r '.id')

USER_TEMPLATE_ID=$(curl -s -X POST "${BASE_URL}/api/v1/prompts" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "flavor-test-user-template",
    "content": "Summarize the following conversation: {{conversation}}",
    "language": "en",
    "is_template": true,
    "template_category": "user"
  }' | jq -r '.id')

REDUCE_TEMPLATE_ID=$(curl -s -X POST "${BASE_URL}/api/v1/prompts" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "flavor-test-reduce-template",
    "content": "Combine these summaries: {{summaries}}",
    "language": "en",
    "is_template": true,
    "template_category": "reduce"
  }' | jq -r '.id')

echo "Provider ID: $PROVIDER_ID"
echo "Model ID: $MODEL_ID"
echo "Service ID: $SERVICE_ID"
echo "System Template ID: $SYSTEM_TEMPLATE_ID"
echo "User Template ID: $USER_TEMPLATE_ID"
echo "Reduce Template ID: $REDUCE_TEMPLATE_ID"
echo ""

# TEST-008-001: Create Flavor with System Template Reference
echo "TEST-008-001: Create Flavor with System Template Reference"
RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/services/${SERVICE_ID}/flavors" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"test-001-flavor-$RANDOM\",
    \"model_id\": \"${MODEL_ID}\",
    \"system_prompt_template_id\": \"${SYSTEM_TEMPLATE_ID}\",
    \"temperature\": 0.7,
    \"top_p\": 0.9,
    \"max_tokens\": 2000,
    \"output_type\": \"text\"
  }")

STATUS=$(echo "$RESPONSE" | jq -r '.id' 2>/dev/null)
if [ "$STATUS" != "null" ] && [ -n "$STATUS" ]; then
  SYSTEM_PROMPT_ID=$(echo "$RESPONSE" | jq -r '.system_prompt_id')
  CONTENT=$(echo "$RESPONSE" | jq -r '.prompt_system_content')
  if [ "$SYSTEM_PROMPT_ID" == "$SYSTEM_TEMPLATE_ID" ] && [ "$CONTENT" == "You are a helpful assistant that summarizes conversations." ]; then
    echo "✅ PASSED: Template reference and content both present"
    ((PASSED++))
  else
    echo "❌ FAILED: Template ID or content missing"
    echo "Expected system_prompt_id=$SYSTEM_TEMPLATE_ID, got=$SYSTEM_PROMPT_ID"
    echo "Expected content='You are a helpful assistant...', got='$CONTENT'"
    ((FAILED++))
  fi
else
  echo "❌ FAILED: Creation failed - $(echo "$RESPONSE" | jq -r '.detail')"
  ((FAILED++))
fi
echo ""

# TEST-008-002: Create Flavor with User Template Reference
echo "TEST-008-002: Create Flavor with User Template Reference"
RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/services/${SERVICE_ID}/flavors" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"test-002-flavor-$RANDOM\",
    \"model_id\": \"${MODEL_ID}\",
    \"user_prompt_template_id\": \"${USER_TEMPLATE_ID}\",
    \"temperature\": 0.8,
    \"top_p\": 0.9,
    \"output_type\": \"text\"
  }")

USER_TMPL_ID=$(echo "$RESPONSE" | jq -r '.user_prompt_template_id')
USER_CONTENT=$(echo "$RESPONSE" | jq -r '.prompt_user_content')
if [ "$USER_TMPL_ID" == "$USER_TEMPLATE_ID" ] && [[ "$USER_CONTENT" == *"Summarize the following conversation"* ]]; then
  echo "✅ PASSED: User template reference works"
  ((PASSED++))
else
  echo "❌ FAILED: User template ID or content missing"
  ((FAILED++))
fi
echo ""

# TEST-008-003: Create Flavor with Multiple Templates
echo "TEST-008-003: Create Flavor with Multiple Templates"
RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/services/${SERVICE_ID}/flavors" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"test-003-flavor-$RANDOM\",
    \"model_id\": \"${MODEL_ID}\",
    \"system_prompt_template_id\": \"${SYSTEM_TEMPLATE_ID}\",
    \"user_prompt_template_id\": \"${USER_TEMPLATE_ID}\",
    \"reduce_prompt_template_id\": \"${REDUCE_TEMPLATE_ID}\",
    \"temperature\": 0.7
  }")

SYS_ID=$(echo "$RESPONSE" | jq -r '.system_prompt_id')
USER_ID=$(echo "$RESPONSE" | jq -r '.user_prompt_template_id')
RED_ID=$(echo "$RESPONSE" | jq -r '.reduce_prompt_id')
if [ "$SYS_ID" == "$SYSTEM_TEMPLATE_ID" ] && [ "$USER_ID" == "$USER_TEMPLATE_ID" ] && [ "$RED_ID" == "$REDUCE_TEMPLATE_ID" ]; then
  echo "✅ PASSED: Multiple templates handled correctly"
  ((PASSED++))
else
  echo "❌ FAILED: Not all template IDs stored"
  ((FAILED++))
fi
echo ""

# TEST-008-004: Create Flavor with Invalid Template ID
echo "TEST-008-004: Create Flavor with Invalid Template ID"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/api/v1/services/${SERVICE_ID}/flavors" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"test-004-flavor-$RANDOM\",
    \"model_id\": \"${MODEL_ID}\",
    \"system_prompt_template_id\": \"00000000-0000-0000-0000-000000000000\",
    \"temperature\": 0.7
  }")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
if [ "$HTTP_CODE" == "404" ]; then
  echo "✅ PASSED: Invalid template ID returns 404"
  ((PASSED++))
else
  echo "❌ FAILED: Expected 404, got $HTTP_CODE"
  ((FAILED++))
fi
echo ""

# TEST-008-005: Create Flavor with Inline Content (No Template)
echo "TEST-008-005: Create Flavor with Inline Content"
RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/services/${SERVICE_ID}/flavors" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"test-005-flavor-$RANDOM\",
    \"model_id\": \"${MODEL_ID}\",
    \"prompt_system_content\": \"Direct inline content without template\",
    \"temperature\": 0.7
  }")

INLINE_CONTENT=$(echo "$RESPONSE" | jq -r '.prompt_system_content')
TEMPLATE_ID=$(echo "$RESPONSE" | jq -r '.system_prompt_id')
if [ "$INLINE_CONTENT" == "Direct inline content without template" ] && [ "$TEMPLATE_ID" == "null" ]; then
  echo "✅ PASSED: Inline content without template works"
  ((PASSED++))
else
  echo "❌ FAILED: Inline content or template ID mismatch"
  ((FAILED++))
fi
echo ""

# TEST-008-006: Set Default Flavor
echo "TEST-008-006: Set Default Flavor"
# Create service with 2 flavors
NEW_SERVICE=$(curl -s -X POST "${BASE_URL}/api/v1/services" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"flavor-test-multi-flavor-$RANDOM\",
    \"route\": \"/test-flavor-test-$RANDOM\",
    \"service_type\": \"summary\",
    \"flavors\": [
      {\"name\": \"Flavor A\", \"model_id\": \"${MODEL_ID}\", \"temperature\": 0.7, \"is_default\": true},
      {\"name\": \"Flavor B\", \"model_id\": \"${MODEL_ID}\", \"temperature\": 0.8, \"is_default\": false}
    ]
  }")

NEW_SERVICE_ID=$(echo "$NEW_SERVICE" | jq -r '.id')
FLAVOR_B_ID=$(echo "$NEW_SERVICE" | jq -r '.flavors[1].id')

# Set Flavor B as default
RESPONSE=$(curl -s -X PATCH "${BASE_URL}/api/v1/services/${NEW_SERVICE_ID}/flavors/${FLAVOR_B_ID}/set-default")
IS_DEFAULT=$(echo "$RESPONSE" | jq -r '.is_default')

# Verify only one default
SERVICE_CHECK=$(curl -s "${BASE_URL}/api/v1/services/${NEW_SERVICE_ID}")
DEFAULT_COUNT=$(echo "$SERVICE_CHECK" | jq '[.flavors[] | select(.is_default == true)] | length')

if [ "$IS_DEFAULT" == "true" ] && [ "$DEFAULT_COUNT" == "1" ]; then
  echo "✅ PASSED: Set default flavor works, only one default exists"
  ((PASSED++))
else
  echo "❌ FAILED: is_default=$IS_DEFAULT, default_count=$DEFAULT_COUNT"
  ((FAILED++))
fi
echo ""

# TEST-008-007: Set Default on Non-Existent Flavor
echo "TEST-008-007: Set Default on Non-Existent Flavor"
RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH "${BASE_URL}/api/v1/services/${SERVICE_ID}/flavors/00000000-0000-0000-0000-000000000000/set-default")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
if [ "$HTTP_CODE" == "404" ]; then
  echo "✅ PASSED: Non-existent flavor returns 404"
  ((PASSED++))
else
  echo "❌ FAILED: Expected 404, got $HTTP_CODE"
  ((FAILED++))
fi
echo ""

# TEST-008-008: Update Flavor with Inline Content
echo "TEST-008-008: Update Flavor with Inline Content"
CREATE_RESP=$(curl -s -X POST "${BASE_URL}/api/v1/services/${SERVICE_ID}/flavors" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"test-008-updatable-$RANDOM\",
    \"model_id\": \"${MODEL_ID}\",
    \"prompt_system_content\": \"Original content\",
    \"temperature\": 0.7
  }")
FLAVOR_ID=$(echo "$CREATE_RESP" | jq -r '.id')

UPDATE_RESP=$(curl -s -X PATCH "${BASE_URL}/api/v1/services/${SERVICE_ID}/flavors/${FLAVOR_ID}" \
  -H "Content-Type: application/json" \
  -d '{"prompt_system_content": "Updated inline content"}')

UPDATED_CONTENT=$(echo "$UPDATE_RESP" | jq -r '.prompt_system_content')
TEMPLATE_ID=$(echo "$UPDATE_RESP" | jq -r '.system_prompt_id')
if [ "$UPDATED_CONTENT" == "Updated inline content" ] && [ "$TEMPLATE_ID" == "null" ]; then
  echo "✅ PASSED: Update flavor inline content works"
  ((PASSED++))
else
  echo "❌ FAILED: Content not updated correctly"
  ((FAILED++))
fi
echo ""

# TEST-008-009: Update Flavor with New Template Reference
echo "TEST-008-009: Update Flavor with New Template Reference"
CREATE_RESP=$(curl -s -X POST "${BASE_URL}/api/v1/services/${SERVICE_ID}/flavors" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"test-009-template-update-$RANDOM\",
    \"model_id\": \"${MODEL_ID}\",
    \"prompt_system_content\": \"Original inline\",
    \"temperature\": 0.7
  }")
FLAVOR_ID=$(echo "$CREATE_RESP" | jq -r '.id')

UPDATE_RESP=$(curl -s -X PATCH "${BASE_URL}/api/v1/services/${SERVICE_ID}/flavors/${FLAVOR_ID}" \
  -H "Content-Type: application/json" \
  -d "{\"system_prompt_template_id\": \"${SYSTEM_TEMPLATE_ID}\"}")

NEW_TEMPLATE_ID=$(echo "$UPDATE_RESP" | jq -r '.system_prompt_id')
NEW_CONTENT=$(echo "$UPDATE_RESP" | jq -r '.prompt_system_content')
if [ "$NEW_TEMPLATE_ID" == "$SYSTEM_TEMPLATE_ID" ] && [[ "$NEW_CONTENT" == *"helpful assistant"* ]]; then
  echo "✅ PASSED: Update flavor with template reference works"
  ((PASSED++))
else
  echo "❌ FAILED: Template not loaded correctly"
  ((FAILED++))
fi
echo ""

# TEST-008-010: Update Flavor Temperature and Max Tokens
echo "TEST-008-010: Update Flavor Temperature and Max Tokens"
CREATE_RESP=$(curl -s -X POST "${BASE_URL}/api/v1/services/${SERVICE_ID}/flavors" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"test-010-params-$RANDOM\",
    \"model_id\": \"${MODEL_ID}\",
    \"temperature\": 0.7,
    \"max_tokens\": 2000
  }")
FLAVOR_ID=$(echo "$CREATE_RESP" | jq -r '.id')

UPDATE_RESP=$(curl -s -X PATCH "${BASE_URL}/api/v1/services/${SERVICE_ID}/flavors/${FLAVOR_ID}" \
  -H "Content-Type: application/json" \
  -d '{"temperature": 1.5, "max_tokens": 4000}')

NEW_TEMP=$(echo "$UPDATE_RESP" | jq -r '.temperature')
NEW_TOKENS=$(echo "$UPDATE_RESP" | jq -r '.max_tokens')
if [ "$NEW_TEMP" == "1.5" ] && [ "$NEW_TOKENS" == "4000" ]; then
  echo "✅ PASSED: Update flavor parameters works"
  ((PASSED++))
else
  echo "❌ FAILED: Parameters not updated (temp=$NEW_TEMP, tokens=$NEW_TOKENS)"
  ((FAILED++))
fi
echo ""

# Summary
echo "========================================"
echo "Flavor Templates QA Test Results"
echo "========================================"
echo "PASSED: $PASSED/10"
echo "FAILED: $FAILED/10"
TOTAL=$((PASSED + FAILED))
PERCENT=$((PASSED * 100 / TOTAL))
echo "Pass Rate: $PERCENT%"
echo ""

if [ $FAILED -eq 0 ]; then
  echo "🎉 All tests passed!"
  exit 0
else
  echo "⚠️  Some tests failed"
  exit 1
fi
