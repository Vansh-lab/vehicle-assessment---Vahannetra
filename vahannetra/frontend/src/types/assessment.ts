export type AnalyzeMediaType = "image" | "video" | "multi";

export type AnalyzeAccepted = {
  job_id: string;
  status: string;
  message: string;
  queued_at: string;
  estimated_seconds?: number;
};

export type AnalyzeInput = {
  media_type?: AnalyzeMediaType;
  source_count?: number;
};

export type AnalyzeUrlInput = {
  source_url: string;
};

export type JobFrame = {
  frame_key: string;
  sharpness: number;
};

export type JobResult = {
  job_id: string;
  status: string;
  input_type: string;
  source_count: number;
  video_key: string;
  created_at: string;
  frames: JobFrame[];
};
