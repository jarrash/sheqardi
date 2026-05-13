/**
 * ProviderPicker
 *
 * Shared provider selection grid used across LLM Evals flows:
 * - ModelsPage "Add model" modal
 * - NewExperimentModal model-under-test and judge steps
 * - EvalsDashboard "Add API key" modal
 *
 * Shows popular provider cards + an "Others" card that opens a searchable
 * autocomplete backed by the live LiteLLM provider list from AI Gateway.
 */

import { FC, useEffect, useRef, useState } from "react";
import {
  Autocomplete,
  Box,
  Card,
  CardContent,
  Collapse,
  Grid,
  TextField,
  Typography,
} from "@mui/material";
import { Check, LayoutGrid } from "lucide-react";
import { evalModelsService } from "../../../../infrastructure/api/evalModelsService";
import { palette } from "../../../themes/palette";

export interface ProviderDef {
  id: string;
  name: string;
  Logo: FC<React.SVGProps<SVGSVGElement>>;
  needsApiKey?: boolean;
}

interface ProviderPickerProps {
  value: string;
  onChange: (id: string) => void;
  /** Popular provider cards shown in the grid */
  providers: ProviderDef[];
  /** Label above the grid */
  label?: string;
  /** Provider ids that already have an API key — shows "Active" badge */
  configuredProviders?: string[];
  /** Grid columns override. Default: xs=4 sm=3 */
  gridColumns?: { xs: number; sm: number };
}

const CARD_SX = {
  "cursor": "pointer",
  "border": "1px solid",
  "backgroundColor": palette.background.main,
  "boxShadow": "none",
  "transition": "all 0.2s ease",
  "position": "relative" as const,
  "height": "100%",
  "&:hover": {
    borderColor: palette.brand.primary,
    boxShadow: "0 2px 6px rgba(0,0,0,0.06)",
  },
};

const CONTENT_SX = {
  "textAlign": "center" as const,
  "py": 3,
  "px": 2,
  "height": "100%",
  "display": "flex",
  "flexDirection": "column" as const,
  "alignItems": "center",
  "justifyContent": "center",
  "&:last-child": { pb: 3 },
};

const ProviderPicker: FC<ProviderPickerProps> = ({
  value,
  onChange,
  providers,
  label = "Model provider",
  configuredProviders = [],
  gridColumns = { xs: 4, sm: 3 },
}) => {
  const popularIds = new Set(providers.map((p) => p.id));
  const isOther = !!value && !popularIds.has(value);
  const [othersOpen, setOthersOpen] = useState(isOther);
  const [allProviders, setAllProviders] = useState<string[]>([]);
  const [loadingProviders, setLoadingProviders] = useState(false);
  const fetched = useRef(false);

  // Keep "Others" panel open if the parent already has a non-popular value
  useEffect(() => {
    if (isOther) setOthersOpen(true);
  }, [isOther]);

  const fetchProviders = async () => {
    if (fetched.current) return;
    fetched.current = true;
    setLoadingProviders(true);
    try {
      const list = await evalModelsService.getGatewayProviders();
      // Filter out popular ones (they're already shown as cards)
      setAllProviders(list.filter((p) => !popularIds.has(p)).sort());
    } finally {
      setLoadingProviders(false);
    }
  };

  const handleOthersClick = () => {
    fetchProviders();
    setOthersOpen(true);
    if (isOther) onChange(""); // clear the non-popular selection so the panel is usable
  };

  return (
    <Box>
      {label && (
        <Typography
          sx={{ mb: 2.5, fontSize: "14px", fontWeight: 500, color: palette.text.secondary }}
        >
          {label}
        </Typography>
      )}

      <Grid container spacing={1.5}>
        {/* Popular provider cards */}
        {providers.map((provider) => {
          const { Logo } = provider;
          const isSelected = value === provider.id;
          const hasKey = configuredProviders.includes(provider.id);

          return (
            <Grid size={gridColumns} key={provider.id}>
              <Card
                onClick={() => {
                  setOthersOpen(false);
                  onChange(provider.id);
                }}
                sx={{
                  ...CARD_SX,
                  borderColor: isSelected ? palette.brand.primary : palette.border.dark,
                }}
              >
                <CardContent sx={CONTENT_SX}>
                  {isSelected && (
                    <Box
                      sx={{
                        position: "absolute",
                        top: 8,
                        right: 8,
                        backgroundColor: palette.brand.primary,
                        borderRadius: "50%",
                        width: 20,
                        height: 20,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      <Check size={12} color={palette.background.main} strokeWidth={3} />
                    </Box>
                  )}

                  {hasKey && !isSelected && (
                    <Box
                      sx={{
                        position: "absolute",
                        top: 6,
                        left: 6,
                        backgroundColor: palette.status.success.bg,
                        borderRadius: "4px",
                        px: 0.75,
                        py: 0.25,
                      }}
                    >
                      <Typography
                        sx={{
                          fontSize: "9px",
                          fontWeight: 600,
                          color: palette.status.success.text,
                          textTransform: "uppercase",
                        }}
                      >
                        Active
                      </Typography>
                    </Box>
                  )}

                  <Box
                    sx={{
                      "display": "flex",
                      "alignItems": "center",
                      "justifyContent": "center",
                      "width": 40,
                      "height": 40,
                      "mb": 1.5,
                      "& svg": { width: 32, height: 32 },
                    }}
                  >
                    <Logo />
                  </Box>

                  <Typography
                    sx={{
                      fontSize: "12px",
                      fontWeight: isSelected ? 600 : 500,
                      color: isSelected ? palette.brand.primary : palette.text.secondary,
                      textAlign: "center",
                    }}
                  >
                    {provider.name}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          );
        })}

        {/* "Others" card */}
        <Grid size={gridColumns}>
          <Card
            onClick={handleOthersClick}
            sx={{
              ...CARD_SX,
              borderColor: isOther || othersOpen ? palette.brand.primary : palette.border.dark,
            }}
          >
            <CardContent sx={CONTENT_SX}>
              {isOther && (
                <Box
                  sx={{
                    position: "absolute",
                    top: 8,
                    right: 8,
                    backgroundColor: palette.brand.primary,
                    borderRadius: "50%",
                    width: 20,
                    height: 20,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Check size={12} color={palette.background.main} strokeWidth={3} />
                </Box>
              )}

              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: 40,
                  height: 40,
                  mb: 1.5,
                }}
              >
                <LayoutGrid
                  size={28}
                  color={isOther || othersOpen ? palette.brand.primary : palette.text.tertiary}
                />
              </Box>

              <Typography
                sx={{
                  fontSize: "12px",
                  fontWeight: isOther || othersOpen ? 600 : 500,
                  color: isOther || othersOpen ? palette.brand.primary : palette.text.secondary,
                  textAlign: "center",
                }}
              >
                {isOther ? value : "Others…"}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Searchable provider autocomplete — shown when "Others" is open */}
      <Collapse in={othersOpen} unmountOnExit>
        <Box sx={{ mt: 2 }}>
          <Autocomplete
            options={allProviders}
            loading={loadingProviders}
            value={isOther ? value : null}
            onChange={(_e, newVal) => {
              if (newVal) onChange(newVal);
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                size="small"
                placeholder="Search providers (e.g. bedrock, azure, cohere)…"
                sx={{
                  "& .MuiOutlinedInput-root": {
                    fontSize: 13,
                    borderRadius: "6px",
                  },
                }}
              />
            )}
            renderOption={(props, option) => (
              <li {...props} key={option} style={{ fontSize: 13 }}>
                {option}
              </li>
            )}
            noOptionsText={loadingProviders ? "Loading providers…" : "No providers found"}
            sx={{ maxWidth: 360 }}
          />
          <Typography sx={{ fontSize: 11, color: palette.text.tertiary, mt: 0.75 }}>
            All LiteLLM-supported providers. You'll need to supply the model name manually.
          </Typography>
        </Box>
      </Collapse>
    </Box>
  );
};

export default ProviderPicker;
