#!/bin/bash
# Test stability by running the demo 10 times consecutively

echo "Testing stability with 10 consecutive runs..."
echo "========================================="

success_count=0
fail_count=0

for i in {1..10}; do
    echo -e "\nRun #$i:"
    if python ../run_once.py --config ../configs/demo.yaml --log-level WARNING > /dev/null 2>&1; then
        echo "✓ Success"
        ((success_count++))
    else
        echo "✗ Failed with exit code $?"
        ((fail_count++))
    fi
done

echo -e "\n========================================="
echo "Results: $success_count successes, $fail_count failures"

if [ $fail_count -eq 0 ]; then
    echo "✅ All runs completed successfully!"
    exit 0
else
    echo "❌ Some runs failed"
    exit 1
fi