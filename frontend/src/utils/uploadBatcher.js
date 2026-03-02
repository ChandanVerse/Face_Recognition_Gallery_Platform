/**
 * Batched Upload Utility
 * Splits large file arrays into chunks and uploads in parallel
 * Prevents server overload and timeouts when uploading thousands of images
 */

const BATCH_SIZE = 30; // Reduced from 100 to 30 for faster response times
const PARALLEL_BATCHES = 5; // Increased from 3 to 5 for better parallelism

export class UploadBatcher {
  constructor(files, uploadFunction, onProgress) {
    this.files = files;
    this.uploadFunction = uploadFunction;
    this.onProgress = onProgress;
    this.batches = this.createBatches();
  }

  /**
   * Split files into batches of BATCH_SIZE
   */
  createBatches() {
    const batches = [];
    for (let i = 0; i < this.files.length; i += BATCH_SIZE) {
      batches.push(this.files.slice(i, i + BATCH_SIZE));
    }
    return batches;
  }

  /**
   * Upload all batches with controlled parallelism
   * Returns summary of results
   */
  async uploadAll() {
    const results = {
      totalFiles: this.files.length,
      totalBatches: this.batches.length,
      uploadedCount: 0,
      failedCount: 0,
      errors: [],
      batchResults: []
    };

    // Upload batches in parallel with concurrency control
    for (let i = 0; i < this.batches.length; i += PARALLEL_BATCHES) {
      // Get the next chunk of batches to upload in parallel
      const batchChunk = this.batches.slice(i, i + PARALLEL_BATCHES);
      const batchStartIndex = i;

      // Upload all batches in this chunk simultaneously
      const batchPromises = batchChunk.map(async (batch, chunkIndex) => {
        const batchNumber = batchStartIndex + chunkIndex + 1;

        try {
          // Upload this batch
          const response = await this.uploadFunction(batch);

          // Track results
          const result = {
            batchNumber,
            success: true,
            response,
            uploadedCount: 0,
            failedCount: 0
          };

          // Update counts (backend returns uploaded_count if available)
          if (response.uploaded_count !== undefined) {
            result.uploadedCount = response.uploaded_count;
            result.failedCount = batch.length - response.uploaded_count;
          } else {
            // Assume all succeeded if backend doesn't report count
            result.uploadedCount = batch.length;
          }

          return result;

        } catch (error) {
          // Batch failed entirely
          return {
            batchNumber,
            success: false,
            error: error.message,
            uploadedCount: 0,
            failedCount: batch.length
          };
        }
      });

      // Wait for all batches in this chunk to complete
      const batchResults = await Promise.allSettled(batchPromises);

      // Process results and update progress
      for (const settledResult of batchResults) {
        const batchResult = settledResult.status === 'fulfilled'
          ? settledResult.value
          : {
              batchNumber: 0,
              success: false,
              error: 'Promise rejected',
              uploadedCount: 0,
              failedCount: 0
            };

        results.batchResults.push(batchResult);
        results.uploadedCount += batchResult.uploadedCount;
        results.failedCount += batchResult.failedCount;

        if (!batchResult.success) {
          results.errors.push(`Batch ${batchResult.batchNumber} failed: ${batchResult.error}`);
        }

        // Update progress callback after each batch completes
        if (this.onProgress) {
          this.onProgress({
            currentBatch: batchResult.batchNumber,
            totalBatches: this.batches.length,
            batchSize: BATCH_SIZE,
            uploadedSoFar: results.uploadedCount,
            totalFiles: this.files.length,
            parallelUploads: PARALLEL_BATCHES
          });
        }
      }
    }

    return results;
  }
}
